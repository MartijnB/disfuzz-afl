#!/usr/bin/python

import multiprocessing
import socket
import urllib
import json
import sys
import random
import os
import shutil
import time
import hashlib
import subprocess
import psutil
import traceback
import requests
import tmuxp

from glob import glob

DISFUZZ_HOST = "https://www.example.com/api/v1"
DISFUZZ_VERSION = "0.1b"

host_config = {
    "hostname": socket.gethostname(),
    "processors": multiprocessing.cpu_count(),
    "amount_auto_projects": multiprocessing.cpu_count(),
    "projects_folder": "./projects",
    "sync_sleep": 120
}

# ---------------------------------------------------------

def list_projects():
    print "Available projects:"

    for project_name in available_projects:
        if is_current_project(project_name):
            if is_project_available(project_name):


                try:
                    if is_project_update_available(project_name):
                        print "-> " + project_name + " (" + available_projects[project_name][
                            "name"] + ") New version available!"
                    else:
                        print "-> " + project_name + " (" + available_projects[project_name]["name"] + ") " + \
                              "Version " + get_current_project_version(project_name) + " " + \
                              "Last update " + time.ctime(
                            os.path.getmtime(get_project_meta_path(project_name) + "/.version"))
                except ApiException:
                    print "-> " + project_name + " (" + available_projects[project_name]["name"] + ")"
            else:
                print "-> " + project_name + " (" + available_projects[project_name]["name"] + ") Not longer available!"
        else:
            print "   " + project_name + " (" + available_projects[project_name]["name"] + ")"


def init_project(project_name):
    print "Init project " + project_name + "..."

    projects = get_available_projects()

    if not project_name in projects:
        print "Error: Unknown project " + project_name + "!"
        return

    try:
        project_info = do_api_request(projects[project_name]["setup_url"])
    except ApiException as e:
        print "Init of project failed!"
        print e
        return

    if is_current_project(project_name):
        print "WARNING: continuing will remove your progress for this project!"
        time.sleep(3)

        shutil.rmtree(get_project_path(project_name))

    os.mkdir(get_project_path(project_name))
    os.mkdir(get_project_meta_path(project_name))
    os.mkdir(get_project_meta_path(project_name) + "/submission")
    os.mkdir(get_project_path(project_name) + "/input")
    os.mkdir(get_project_path(project_name) + "/output")
    os.mkdir(get_project_path(project_name) + "/output/import")
    os.mkdir(get_project_path(project_name) + "/output/import/queue")

    store_current_project_info(project_name, project_info)
    update_project_files(project_name)

    if os.path.exists(get_project_path(project_name) + "/init.sh"):
        os.chmod(get_project_path(project_name) + "/init.sh", 0744)

        psutil.Popen("./init.sh", shell=True, cwd=get_project_path(project_name)).wait()

    print "Project " + project_name + " is now ready to run!"


def update_project(project_name):
    print "Update project " + project_name + "..."

    if not project_name in get_available_projects():
        print "Error: Project " + project_name + " is not longer available!"
        return

    try:
        project_info = get_latest_project_info(project_name)
    except ApiException as e:
        print "Update of project failed!"
        print e
        return

    current_version = get_current_project_version(project_name)

    store_current_project_info(project_name, project_info)
    update_project_files(project_name)

    if os.path.exists(get_project_path(project_name) + "/upgrade.sh"):
        os.chmod(get_project_path(project_name) + "/upgrade.sh", 0744)

        psutil.Popen("./upgrade.sh", shell=True, cwd=get_project_path(project_name)).wait()

    if current_version != get_current_project_version(project_name):
        print "Updated " + project_name + " to version " + get_current_project_version(project_name) + "!"
    else:
        print "Nothing to update"


def update_project_files(project_name):
    try:
        project_files_info = get_latest_project_file_info(project_name)
    except ApiException as e:
        print "Update of project files failed!"
        print e
        return

    for file_info in project_files_info["files"]:
        if not os.path.exists(get_project_path(project_name) + file_info["path"]):
            try:
                os.stat(get_project_path(project_name) + os.path.dirname(file_info["path"]))
            except:
                os.makedirs(get_project_path(project_name) + os.path.dirname(file_info["path"]))

            print "Downloading " + file_info["path"] + "..."

            urllib.urlretrieve(file_info["url"],
                               get_project_path(project_name) + file_info["path"])
        elif md5sum(get_project_path(project_name) + file_info["path"]) != file_info["md5sum"]:
            print "Updating " + file_info["path"] + "..."

            os.unlink(get_project_path(project_name) + file_info["path"])

            urllib.urlretrieve(file_info["url"],
                               get_project_path(project_name) + file_info["path"])
        else:
            print "Skipped " + file_info["path"]

    store_current_project_version(project_name, project_files_info["version"])


def update_project_testcases(project_name):
    try:
        project_queue_submissions = get_current_project_queue_submission_state(project_name)
    except:
        project_queue_submissions = []

    try:
        project_testcases_info = get_latest_project_testcases_info(project_name)
    except ApiException as e:
        print "Update of project testcases failed!"
        print e
        return

    for file_info in project_testcases_info["files"]:
        while "::" in file_info["path"]:
            file_info["path"] = file_info["path"].split("::")[1]

        if file_info["md5sum"] not in project_queue_submissions:  # We don't want our own queue submissions back
            if not os.path.exists(get_project_path(project_name) + "/output/import/queue/" + file_info["path"]):
                try:
                    os.stat(
                        get_project_path(project_name) + "/output/import/queue/" + os.path.dirname(file_info["path"]))
                except:
                    os.makedirs(
                        get_project_path(project_name) + "/output/import/queue/" + os.path.dirname(file_info["path"]))

                print "Downloading " + file_info["path"] + "..."

                urllib.urlretrieve(file_info["url"],
                                   get_project_path(project_name) + "/output/import/queue/" + file_info["path"])


def sync_project(project_name, exclude_testcases=False):
    if not exclude_testcases:
        update_project_testcases(project_name)

    submit_project_queue(project_name)
    submit_project_hangs(project_name)
    submit_project_crashes(project_name)
    submit_project_instance_stats(project_name)


def submit_project_hangs(project_name):
    project_info = get_current_project_info(project_name)

    try:
        project_hang_submissions = get_current_project_hang_submission_state(project_name)
    except:
        project_hang_submissions = []

    for instance_path in glob(get_project_path(project_name) + "/output/*"):
        if os.path.isdir(instance_path) and os.path.basename(instance_path) != "import":
            for hang_file_path in glob(instance_path + "/hangs/*"):
                hang_file_path_md5sum = md5sum(hang_file_path)

                if hang_file_path_md5sum not in project_hang_submissions:
                    print "Submitting " + hang_file_path + "..."

                    requests.post(project_info["hang_submit_url"],
                                  files={"file": open(hang_file_path, 'rb')})

                    project_hang_submissions.append(hang_file_path_md5sum)
                else:  # we have seen this or submitted this before, delete it
                    os.unlink(hang_file_path)

    store_current_project_hang_submission_state(project_name, project_hang_submissions)


def submit_project_crashes(project_name):
    project_info = get_current_project_info(project_name)

    try:
        project_crash_submissions = get_current_project_crash_submission_state(project_name)
    except:
        project_crash_submissions = []

    for instance_path in glob(get_project_path(project_name) + "/output/*"):
        if os.path.isdir(instance_path) and os.path.basename(instance_path) != "import":
            for crash_file_path in glob(instance_path + "/crashes/*"):
                crash_file_path_md5sum = md5sum(crash_file_path)

                if crash_file_path_md5sum not in project_crash_submissions:
                    print "Submitting " + crash_file_path + "..."

                    requests.post(project_info["crash_submit_url"],
                                  files={"file": open(crash_file_path, 'rb')})

                    project_crash_submissions.append(crash_file_path_md5sum)
                else:  # we have seen this or submitted this before, delete it
                    os.unlink(crash_file_path)

    store_current_project_crash_submission_state(project_name, project_crash_submissions)


def submit_project_queue(project_name):
    project_info = get_current_project_info(project_name)

    try:
        project_queue_submissions = get_current_project_queue_submission_state(project_name)
    except:
        project_queue_submissions = []

    for instance_path in glob(get_project_path(project_name) + "/output/*"):
        if os.path.isdir(instance_path) and os.path.basename(instance_path) != "import":
            for queue_file_path in glob(instance_path + "/queue/*"):
                queue_file_path_md5sum = md5sum(queue_file_path)

                if queue_file_path_md5sum not in project_queue_submissions:
                    print "Submitting " + queue_file_path + "..."

                    requests.post(project_info["queue_submit_url"],
                                  files={"file": open(queue_file_path, 'rb')})

                    project_queue_submissions.append(queue_file_path_md5sum)

    store_current_project_queue_submission_state(project_name, project_queue_submissions)


def submit_project_instance_stats(project_name):
    project_info = get_current_project_info(project_name)

    for fp in glob(get_project_path(project_name) + "/output/*/fuzzer_stats"):
        requests.post(project_info["session_submit_url"],
                      files={"file": (os.path.basename(os.path.dirname(fp)), open(fp, 'rb'))})


def is_current_project(project_name):
    try:
        os.stat(get_project_path(project_name))
        return True
    except:
        return False


def is_project_update_available(project_name):
    return get_latest_project_version(project_name) != get_current_project_version(project_name)


def is_project_running(project_name):
    try:
        project_state = get_current_project_state(project_name)

        is_running = False

        for pid in project_state["pid"]:
            if psutil.pid_exists(pid):
                is_running = True

        return is_running
    except:
        return False


def is_project_finished(project_name):
    try:
        os.stat(get_project_path(project_name) + "/.meta/.finished")
        return True
    except:
        return False


def start_project_instance(project_name, start_as_master=False, use_tmux=False):
    if not os.path.exists(get_project_path(project_name) + "/run.sh"):
        raise Exception("Missing run.sh!")

    try:
        if os.path.exists(get_project_meta_path(project_name) + "/.last_pid"):
            os.unlink(get_project_meta_path(project_name) + "/.last_pid")

        os.chmod(get_project_path(project_name) + "/run.sh", 0744)

        if use_tmux:
            start_cmd = "exec ./run.sh"
            window_name = "slave"

            if start_as_master:
                start_cmd += " -master"
                window_name = "master"

            tmux_server = tmuxp.Server(socket_path=get_project_meta_path(project_name) + "/.tmux_socket")

            if tmux_server.has_session(project_name):
                tmux_session = tmux_server.findWhere({"session_name": project_name})
                tmux_window = tmux_session.new_window(attach=True)
                tmux_pane = tmux_window.attached_pane()
            else:
                tmux_session = tmux_server.new_session(session_name=project_name)
                tmux_window = tmux_session.attached_window()
                tmux_pane = tmux_window.attached_pane()

            tmux_window.rename_window(window_name)
            tmux_pane.send_keys("cd " + get_project_path(project_name))
            tmux_pane.send_keys("echo $$ > ./.meta/.last_pid")
            tmux_pane.send_keys(start_cmd)

            while not os.path.exists(get_project_meta_path(project_name) + "/.last_pid"):
                pass

            with open(get_project_meta_path(project_name) + "/.last_pid", "r") as f:
                last_pid = int(f.read().strip())

            tmux_window.rename_window(window_name + " (" + str(last_pid) + ")")

            handle = psutil.Process(last_pid)
        else:
            start_cmd = ["exec ./run.sh"]

            if start_as_master:
                start_cmd.append("-master")

            handle = psutil.Popen(start_cmd,
                                  shell=True,
                                  cwd=get_project_path(project_name),
                                  stdout=subprocess.PIPE)  # stderr=subprocess.PIPE

        # Add the new pid to the state file so we can kill it in the future
        state = {"pid": []}

        try:
            state = get_current_project_state(project_name)
        except:
            pass

        state["pid"].append(handle.pid)

        store_current_project_state(project_name, state)
    except Exception as e:
        print e
        return False

    return handle


def stop_project_all_instances(project_name):
    try:
        project_state = get_current_project_state(project_name)

        for pid in project_state["pid"]:
            if psutil.pid_exists(pid):
                print "Killing " + str(pid) + "..."

                kill_process_with_children(psutil.Process(pid))

        # kill the tmux server if it's running
        tmux_server = tmuxp.Server(socket_path=get_project_meta_path(project_name) + "/.tmux_socket")

        if tmux_server.has_session(project_name):
            tmux_server.kill_session(project_name)

        project_state["pid"] = []

        store_current_project_state(project_name, project_state)
    except Exception as e:
        print e
        pass


def stop_project_instance(project_name, handle):
    if handle.is_running():
        print "Killing " + str(handle.pid) + "..."

        kill_process_with_children(handle)

    cleanup_project_instance(project_name, handle)


def cleanup_project_instance(project_name, handle):
    project_state = get_current_project_state(project_name)

    if handle.pid in project_state["pid"]:
        project_state["pid"].remove(handle.pid)

    store_current_project_state(project_name, project_state)


def get_project_path(project_name):
    return host_config["projects_folder"] + "/" + project_name


def get_project_meta_path(project_name):
    return get_project_path(project_name) + "/.meta"


def get_current_project_info(project_name):
    with open(get_project_meta_path(project_name) + "/.session", "r") as f:
        return json.load(f)


def store_current_project_info(project_name, project_info):
    with open(get_project_meta_path(project_name) + "/.session", "w") as f:
        json.dump(project_info, f)


def get_current_project_version(project_name):
    with open(get_project_meta_path(project_name) + "/.version", "r") as f:
        return json.load(f)


def store_current_project_version(project_name, version_info):
    with open(get_project_meta_path(project_name) + "/.version", "w") as f:
        json.dump(version_info, f)


def get_current_project_state(project_name):
    with open(get_project_meta_path(project_name) + "/.state", "r") as f:
        return json.load(f)


def store_current_project_state(project_name, state):
    with open(get_project_meta_path(project_name) + "/.state", "w") as f:
        json.dump(state, f)


def get_current_project_hang_submission_state(project_name):
    with open(get_project_meta_path(project_name) + "/submission/.hangs", "r") as f:
        return json.load(f)


def store_current_project_hang_submission_state(project_name, state):
    with open(get_project_meta_path(project_name) + "/submission/.hangs", "w") as f:
        json.dump(state, f)


def get_current_project_crash_submission_state(project_name):
    with open(get_project_meta_path(project_name) + "/submission/.crashes", "r") as f:
        return json.load(f)


def store_current_project_crash_submission_state(project_name, state):
    with open(get_project_meta_path(project_name) + "/submission/.crashes", "w") as f:
        json.dump(state, f)


def get_current_project_queue_submission_state(project_name):
    with open(get_project_meta_path(project_name) + "/submission/.queue", "r") as f:
        return json.load(f)


def store_current_project_queue_submission_state(project_name, state):
    with open(get_project_meta_path(project_name) + "/submission/.queue", "w") as f:
        json.dump(state, f)


available_projects = {}


def get_available_projects():
    return available_projects


def update_available_projects():
    global available_projects

    available_projects = do_api_request(DISFUZZ_HOST + "?c=" + host_config["hostname"])


def amount_available_projects():
    return len(available_projects)


def is_project_available(project_name):
    return project_name in available_projects


def get_current_projects():
    project_folders = glob(host_config["projects_folder"] + "/*/.meta/.session")
    projects = []

    for f in project_folders:
        projects.append(
            os.path.dirname(os.path.dirname(f)).replace(host_config["projects_folder"], "").replace("/", ""))

    return projects


def get_latest_project_info(project_name):
    project_info = get_current_project_info(project_name)

    return do_api_request(project_info["session_update_url"])


def get_latest_project_file_info(project_name):
    project_info = get_current_project_info(project_name)

    return do_api_request(project_info["files_url"])


def get_latest_project_testcases_info(project_name):
    project_info = get_current_project_info(project_name)

    return do_api_request(project_info["queue_download_url"])


def get_latest_project_version(project_name):
    project_file_info = get_latest_project_file_info(project_name)

    return project_file_info["version"]


class ApiException(Exception):
    pass


def do_api_request(url):
    api_result = json.loads(urllib.urlopen(url).read())

    if "error" in api_result:
        raise ApiException("Error: Can't load data from API!\nAPI error: " + api_result["error"])

    return api_result


def md5sum(p):
    m = hashlib.md5()

    with open(p, 'rb') as f:
        while True:
            d = f.read(8192)
            if not d:
                break
            m.update(d)

    return m.hexdigest()


def sha1sum(p):
    m = hashlib.sha1()

    with open(p, 'rb') as f:
        while True:
            d = f.read(8192)
            if not d:
                break
            m.update(d)

    return m.hexdigest()


def kill_process_with_children(process_handle):
    for child_handle in process_handle.children(recursive=True):
        try:
            child_handle.kill()
        except psutil.NoSuchProcess:
            pass

    try:
        process_handle.kill()
    except psutil.NoSuchProcess:
        pass


# ---------------------------------------------------------

print "DisFuzz " + DISFUZZ_VERSION

if not os.path.exists(host_config["projects_folder"]):
    os.makedirs(host_config["projects_folder"])

try:
    update_available_projects()
except Exception as e:
    print "It was not possible to load the list with available projects!"
    print e
    sys.exit()

if len(sys.argv) == 2 and sys.argv[1] == "list":
    list_projects()
elif len(sys.argv) == 3 and sys.argv[1] == "init":
    init_project(sys.argv[2])
elif len(sys.argv) >= 2 and sys.argv[1] == "sync":
    if len(sys.argv) == 2 or (len(sys.argv) == 3 and sys.argv[2] == "all"):
        for p in get_current_projects():
            print "Sync " + p + "..."

            sync_project(p)

            print "Sync completed!"
    elif is_current_project(sys.argv[2]):
        sync_project(sys.argv[2])

        print "Sync completed!"
    else:
        print "Unknown project " + sys.argv[2] + "!"
elif len(sys.argv) >= 2 and sys.argv[1] == "monitor":
    if len(sys.argv) == 2 or (len(sys.argv) == 3 and sys.argv[2] == "all"):
        print "Monitoring:"
        for p in get_current_projects():
            if is_project_running(p):
                print p

        while True:
            try:
                time.sleep(host_config["sync_sleep"])

                for p in get_current_projects():
                    if is_project_running(p):
                        sync_project(p)

                        if is_project_update_available(p):
                            print "Update available for " + p + "!"
            except KeyboardInterrupt:
                sys.exit()
            except Exception as e:
                print "Unknown error! Ignore for now..."
                print e
                traceback.print_exc()
    elif is_current_project(sys.argv[2]):
        print "Monitoring of " + sys.argv[2] + " started!"

        while True:
            try:
                time.sleep(host_config["sync_sleep"])

                if is_project_running(sys.argv[2]):
                    sync_project(sys.argv[2])

                    if is_project_update_available(sys.argv[2]):
                        print "Update available for " + sys.argv[2] + "!"
            except KeyboardInterrupt:
                sys.exit()
            except Exception as e:
                print "Unknown error! Ignore for now..."
                print e
                traceback.print_exc()
    else:
        print "Unknown project " + sys.argv[2] + "!"
elif len(sys.argv) >= 2 and sys.argv[1] == "update":
    if len(sys.argv) == 2 or (len(sys.argv) == 3 and sys.argv[2] == "all"):
        for p in get_current_projects():
            if not is_project_running(p):
                update_project(p)
            else:
                print "Project " + p + " is running, update skipped."
    elif is_current_project(sys.argv[2]):
        if not is_project_running(sys.argv[2]):
            update_project(sys.argv[2])
        else:
            print "Project " + sys.argv[2] + " is running, update skipped."
    else:
        print "Unknown project " + sys.argv[2] + "!"
elif len(sys.argv) >= 2 and sys.argv[1] == "sessions":
    if len(sys.argv) == 2 or (len(sys.argv) == 3 and sys.argv[2] == "all"):
        for p in get_current_projects():
            tmux_server = tmuxp.Server(socket_path=get_project_meta_path(p) + "/.tmux_socket")

            if is_project_running(p) and tmux_server.has_session(p):
                print p + " instances:"

                tmux_session = tmux_server.findWhere({"session_name": p})

                for w in tmux_session.list_windows():
                    print "\t" + w.get("window_name")
    elif is_current_project(sys.argv[2]):
        tmux_server = tmuxp.Server(socket_path=get_project_meta_path(sys.argv[2]) + "/.tmux_socket")

        if is_project_running(sys.argv[2]) and tmux_server.has_session(sys.argv[2]):
            print sys.argv[2] + " instances:"

            tmux_session = tmux_server.findWhere({"session_name": sys.argv[2]})

            for w in tmux_session.list_windows():
                print "\t" + w.get("window_name")
    else:
        print "Unknown project " + sys.argv[2] + "!"
elif len(sys.argv) >= 3 and sys.argv[1] == "start":
    if not tmuxp.util.has_required_tmux_version():
        print "tmux version too old!"
        sys.exit()

    if is_current_project(sys.argv[2]):
        # if not is_project_running(sys.argv[2]):
        if len(sys.argv) == 4 and sys.argv[3] == "-m":
            if start_project_instance(sys.argv[2], use_tmux=True, start_as_master=True):
                print "Started!\nDon't forget to start a monitor session."
            else:
                print "Failed to start " + sys.argv[2] + "!"
        else:
            if start_project_instance(sys.argv[2], use_tmux=True):
                print "Started!\nDon't forget to start a monitor session."
            else:
                print "Failed to start " + sys.argv[2] + "!"
                # else:
                # print "Project " + sys.argv[2] + " is currently already running!"
    else:
        print "Unknown project " + sys.argv[2] + "!"
elif len(sys.argv) >= 2 and sys.argv[1] == "stop":
    if len(sys.argv) == 2 or (len(sys.argv) == 3 and sys.argv[2] == "all"):
        for p in get_current_projects():
            # if is_project_running(p):
            print "Stopping " + p + "..."
            stop_project_all_instances(p)
    elif is_current_project(sys.argv[2]):
        # if is_project_running(sys.argv[2]):
        print "Stopping " + sys.argv[2] + "..."

        stop_project_all_instances(sys.argv[2])
        # else:
        # print "Project " + sys.argv[2] + " is currently not running!"
    else:
        print "Unknown project " + sys.argv[2] + "!"
elif len(sys.argv) == 3 and sys.argv[1] == "console":
    if is_current_project(sys.argv[2]):
        tmux_server = tmuxp.Server(socket_path=get_project_meta_path(sys.argv[2]) + "/.tmux_socket")

        if is_project_running(sys.argv[2]) and tmux_server.has_session(sys.argv[2]):
            tmux_session = tmux_server.findWhere({"session_name": sys.argv[2]})

            tmux_session.attach_session()
        else:
            print "Project " + sys.argv[2] + " is not running!"
    else:
        print "Unknown project " + sys.argv[2] + "!"
elif len(sys.argv) == 2 and sys.argv[1] == "auto":
    print "Detecting host information..."
    print "Amount processors: " + str(host_config["processors"])
    print "Hostname: " + host_config["hostname"]

    # update or init a few projects
    current_projects = get_current_projects()

    if len(current_projects):
        print "Current projects:"

        for p in current_projects:
            print "-> " + p

        print "Updating..."

        for p in current_projects:
            update_project(p)
    else:
        amount_available_projects = amount_available_projects()
        max_projects = host_config["amount_auto_projects"]

        list_projects()

        print "Looks this is the first time you use this. Lets bootstrap (maximum) " + str(
            host_config["amount_auto_projects"]) + " random from a total of " + str(
            amount_available_projects) + " projects..."

        projects = []
        for project_name in get_available_projects():
            available_projects[project_name]["__internal_name"] = project_name
            projects.append(available_projects[project_name])

        random.shuffle(projects)

        i = 0;
        while i < max_projects and len(projects) > 0:
            init_project(projects[0]["__internal_name"])

            del projects[0]

            i += 1

    # now its time to start them
    print "Downloading queue..."

    for p in current_projects:
        update_project_testcases(p)

    print "Start projects..."

    running_project_handles = []
    for p in get_current_projects():
        if not is_project_running(p):
            print "Starting " + p + "..."

            project_handle = start_project_instance(p)

            if project_handle:
                running_project_handles.append({
                    "project_name": p,
                    "handle": project_handle
                })

                time.sleep(10)
            else:
                print "Failed to start " + p + "!"
        else:
            print "Skipped " + p + "! Is it still running?\n"

    print str(len(running_project_handles)) + " instance(s) started!"

    print "WARNING: Leave this process running!"

    while True:
        try:
            time.sleep(host_config["sync_sleep"])

            # Check for crashed projects
            for rpi in running_project_handles:
                if not rpi["handle"].is_running():
                    cleanup_project_instance(rpi["project_name"], rpi["handle"])

                    if not is_project_finished(rpi["project_name"]):
                        print "Project " + rpi["project_name"] + " has stopped prematurely!"
                        print "Return code: " + str(rpi["handle"].returncode)

                        running_project_handles.remove(rpi)

                        print "Restarting " + p + "..."

                        project_handle = start_project_instance(p)

                        if project_handle:
                            running_project_handles.append({
                                "project_name": p,
                                "handle": project_handle
                            })
                        else:
                            print "Failed to start " + p + "!"

            # Some small maintenance
            for p in get_current_projects():
                if is_project_running(p):
                    sync_project(p)

                if is_project_update_available(p):
                    print "Update available for " + p + "!"
                    print "Restarting " + p + "..."

                    stop_project_all_instances(p)

                    for rpi in running_project_handles:
                        if rpi["project_name"] == p:
                            running_project_handles.remove(rpi)

                    update_project(p)

                    project_handle = start_project_instance(p)

                    if project_handle:
                        running_project_handles.append({
                            "project_name": p,
                            "handle": project_handle
                        })
                    else:
                        print "Failed to start " + p + "!"
        except KeyboardInterrupt:
            print "Uploading the queue, hangs & crashes..."

            for p in get_current_projects():
                if is_project_running(p):
                    sync_project(p, exclude_testcases=True)

            print "Killing the running processes..."

            for rpi in running_project_handles:
                print "Stopping " + rpi["project_name"] + "..."

                if rpi["handle"].is_running():
                    stop_project_instance(rpi["project_name"], rpi["handle"])

            sys.exit()
        except Exception as e:
            print "Unknown error! Ignore for now..."
            print e
            traceback.print_exc()
else:
    print
    print "Usage: " + sys.argv[0] + " [command]\n"
    print "Commands:\n"
    print "auto\t\t\t\tInit or update a couple of projects and start fuzzing"
    print
    print "list\t\t\t\tShow the available projects."
    print "sessions [<projectname>]\tList the instances of a project"
    print "console <projectname>\t\tOpen a console to the project instances"
    print
    print "init <projectname>\t\tInit a project"
    print "update [all|<projectname>]\tUpdate the project to the latest version"
    print
    print "start <projectname> [-m]\tStart a new instance (use -m to start a master instance)"
    print "stop [all|<projectname>]\tStop all instances"
    print
    print "sync [all|<projectname>]\tSync all or a single instance"
    print "monitor [all|<projectname>]\tContinuously sync all or a single running instance"
    print