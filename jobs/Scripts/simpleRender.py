import argparse
import os
import subprocess
import psutil
import json
import importlib.util
from datetime import datetime
from shutil import copyfile, rmtree
import traceback
import sys
import time
from subprocess import PIPE, STDOUT
import signal
import re
import threading
from ffmpy improt FFmpeg

from utils import *

ROOT_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir))
sys.path.append(ROOT_PATH)
from jobs_launcher.core.config import *
from jobs_launcher.core.system_info import get_gpu


def copy_test_cases(args):
    try:
        copyfile(os.path.realpath(os.path.join(os.path.dirname(
            __file__), '..', 'Tests', args.test_group, 'test_cases.json')),
            os.path.realpath(os.path.join(os.path.abspath(
                args.output), 'test_cases.json')))

        cases = json.load(open(os.path.realpath(
            os.path.join(os.path.abspath(args.output), 'test_cases.json'))))

        with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
            cases = json.load(json_file)
    except Exception as e:
        main_logger.error('Can\'t load test_cases.json')
        main_logger.error(str(e))
        exit(-1)


def prepare_empty_reports(args):
    main_logger.info('Create empty report files')

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    for case in cases:
        if case['status'] != 'done' and case['status'] != 'error':
            if case["status"] == 'inprogress':
                case['status'] = 'active'

            test_case_report = {}
            test_case_report['test_case'] = case['case']
            test_case_report['render_device'] = get_gpu()
            test_case_report['script_info'] = case['script_info']
            test_case_report['test_group'] = args.test_group
            test_case_report['tool'] = 'SVL Simulator'
            test_case_report['render_time'] = 0.0
            test_case_report['execution_time'] = 0.0
            test_case_report['date_time'] = datetime.now().strftime(
                '%m/%d/%Y %H:%M:%S')
            test_case_report["number_of_tries"] = 0
            test_case_report["message"] = []

            if case['status'] == 'skipped':
                test_case_report['test_status'] = 'skipped'
                test_case_report['group_timeout_exceeded'] = False
            else:
                test_case_report['test_status'] = 'error'

            case_path = os.path.join(args.output, case['case'] + CASE_REPORT_SUFFIX)

            if os.path.exists(case_path):
                with open(case_path) as f:
                    case_json = json.load(f)[0]
                    test_case_report["number_of_tries"] = case_json["number_of_tries"]

            with open(case_path, "w") as f:
                f.write(json.dumps([test_case_report], indent=4))

    with open(os.path.join(args.output, "test_cases.json"), "w+") as f:
        json.dump(cases, f, indent=4)


def save_results(args, case, cases, execution_time = 0.0, test_case_status = "", error_messages = []):
    with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "r") as file:
        test_case_report = json.loads(file.read())[0]

        test_case_report["test_status"] = test_case_status

        test_case_report["execution_time"] = execution_time

        test_case_report["log"] = os.path.join("tool_logs", case["case"] + ".log")

        test_case_report["testing_start"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        test_case_report["number_of_tries"] += 1

        test_case_report["message"] = test_case_report["message"] + list(error_messages)

        if test_case_report["test_status"] == "passed" or test_case_report["test_status"] == "error":
            test_case_report["group_timeout_exceeded"] = False

        video_path = os.path.join("Color", case["case"] + ".mp4")

        if os.path.exists(os.path.join(args.output, video_path)):
            test_case_report[VIDEO_KEY] = video_path

    with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "w") as file:
        json.dump([test_case_report], file, indent=4)

    if test_case_status:
       case["status"] = test_case_status

    with open(os.path.join(args.output, "test_cases.json"), "w") as file:
        json.dump(cases, file, indent=4)


def record_video(descriptor):
    descriptor.run()


def start_svl_simulator(simulator_path):
    simulator_process = psutil.Popen(simulator_path, stdout=PIPE, stderr=PIPE, shell=True)

    init_process = psutil.Popen("sh svlsim.sh cli initialize", stdout=PIPE, stderr=PIPE, shell=True)
    out, err = init_process.communicate()

    main_logger.info("Init process out: {}".format(out))
    main_logger.info("Init process err: {}".format(err))

    if init_process.returncode != 0:
        raise Exception("Failed to run init script")

    simulation_start_process = psutil.Popen("sh svlsim.sh simulation start {}".format(args.simulation_id), stdout=PIPE, stderr=PIPE, shell=True)
    out, err = simulation_start_process.communicate()

    main_logger.info("Simulation start process out: {}".format(out))
    main_logger.info("Simulation start process err: {}".format(err))

    if simulation_start_process.returncode != 0:
        raise Exception("Failed to start simulation")

    return simulator_process


def execute_tests(args):
    rc = 0

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    tool_path = os.path.abspath(args.tool)

    simulator_process = None

    try:
        spec = importlib.util.find_spec("extensions." + args.test_group)
        group_module = importlib.util.module_from_spec(spec)
        sys.modules["group_module"] = group_module
        spec.loader.exec_module(group_module)

        for case in [x for x in cases if x != "skipped"]:

            case_start_time = time.time()

            current_try = 0

            error_messages = set()

            video_recording_descriptor = None
            video_thread = None

            while current_try < args.retries:
                try:
                    main_logger.info("Start test case {}. Try: {}".format(case["case"], current_try))

                    if simulator_process is None:
                        # start SVL simulator
                        main_logger.info("Start SVL simulator")
                        simulator_process = start_svl_simulator(tool_path)

                    video_path = os.path.join(args.output, "Color", case["case"] + ".mp4")

                    if os.path.exists(video_path):
                        os.remove(video_path)

                    video_recording_descriptor = FFmpeg(
                        outputs = {video_path: ['-video_size', '1920x1080', '-f', 'x11grab', '-i', ':0.0']}
                    )

                    video_thread = threading.Thread(target=record_video, args=(video_recording_descriptor,))
                    video_thread.start()

                    for function in case["functions"]:
                        if re.match("((^\S+|^\S+ \S+) = |^print|^if|^for|^with)", function):
                            exec(function)
                        else:
                            eval(function)

                    execution_time = time.time() - case_start_time
                    save_results(args, case, cases, execution_time = execution_time, test_case_status = "passed", error_messages = [])

                    break
                except Exception as e:
                    if simulator_process is not None:
                        close_process(simulator_process)
                        simulator_process = None

                    execution_time = time.time() - case_start_time
                    save_results(args, case, cases, execution_time = execution_time, test_case_status = "failed", error_messages = error_messages)
                    main_logger.error("Failed to execute test case (try #{}): {}".format(current_try, str(e)))
                    main_logger.error("Traceback: {}".format(traceback.format_exc()))
                finally:
                    if video_recording_descriptor is not None:
                        video_recording_descriptor.process.terminate()
                        video_recording_descriptor = None

                    current_try += 1
            else:
                main_logger.error("Failed to execute case '{}' at all".format(case["case"]))
                rc = -1
                execution_time = time.time() - case_start_time
                save_results(args, case, cases, execution_time = execution_time, test_case_status = "error", error_messages = error_messages)

    except Exception as e:
        main_logger.error("Failed to run tests: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))

    finally:
        if simulator_process is not None:
            close_process(simulator_process)
            simulator_process = None

    return rc


def createArgsParser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--tool", required=True)
    parser.add_argument("--output", required=True, metavar="<dir>")
    parser.add_argument("--test_group", required=True)
    parser.add_argument("--simulation_id", required=True)
    parser.add_argument("--retries", required=False, default=2, type=int)

    return parser


if __name__ == '__main__':
    main_logger.info('simpleRender start working...')

    args = createArgsParser().parse_args()

    try:
        os.makedirs(args.output)

        if not os.path.exists(os.path.join(args.output, "Color")):
            os.makedirs(os.path.join(args.output, "Color"))
        if not os.path.exists(os.path.join(args.output, "tool_logs")):
            os.makedirs(os.path.join(args.output, "tool_logs"))

        copy_test_cases(args)
        prepare_empty_reports(args)
        exit(execute_tests(args))
    except Exception as e:
        main_logger.error("Failed during script execution. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        exit(-1)