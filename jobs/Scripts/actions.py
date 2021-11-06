import json


def set_passed(case_json_path):
    with open(case_json_path, "r") as file:
        test_case_report = json.loads(file.read())[0]

        test_case_report["test_status"] = "passed"

    with open(case_json_path, "w") as file:
        json.dump([test_case_report], file, indent=4)


def set_error(case_json_path, error_message):
    with open(case_json_path, "r") as file:
        test_case_report = json.loads(file.read())[0]

        test_case_report["test_status"] = "error"
        test_case_report["message"].append(error_message)

    with open(case_json_path, "w") as file:
        json.dump([test_case_report], file, indent=4)
