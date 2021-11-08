import json
import os
import argparse
import glob
import sys


sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))

import jobs_launcher.core.performance_parser as perf_parser


def metrics_stat(work_dir):
    metrics_report = []
    metrics_dir = os.path.join('metrics_logs')
    metric_files = glob.glob(os.path.join(metrics_dir, '*.log'))
    report_files = glob.glob(os.path.join(work_dir, '*_RPR.json'))

    for metric_file in metric_files:
        intervals_dict = {}

        for report_file in report_files:
            with open(report_file, 'r') as f:
                report = json.load(f)[0]

                intervals_dict[report['test_case']] = (report['render_start_time'], report['render_end_time'])

        metrics_report.append({
            'metric': os.path.basename(metric_file).split('.log')[0],
            'cases': perf_parser.parse_cases_metric(metric_file, intervals_dict)
        })

    with open(os.path.realpath(os.path.join(work_dir, '..', os.path.basename(work_dir) + '_metrics.json')), 'w') as f:
        json.dump(metrics_report, f, indent=4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work_dir', required=True)
    args = parser.parse_args()
    work_dir = args.work_dir

    metrics_stat(work_dir)

    json_files = list(
        filter(
            lambda x: x.endswith('RPR.json'), os.listdir(work_dir)
        )
    )

    reports = []

    for file in json_files:
        json_content = json.load(open(os.path.join(work_dir, file), 'r'))[0]

        if json_content.get('group_timeout_exceeded', False):
            json_content['message'].append('Test group timeout exceeded')


        reports.append(json_content)
    with open(os.path.join(work_dir, 'report_compare.json'), 'w') as f: json.dump(reports, f, indent=4)
