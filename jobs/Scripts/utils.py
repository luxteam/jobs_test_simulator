from time import sleep
import psutil


def close_process(process):
    child_processes = []

    try:
        child_processes = process.children()
    except psutil.NoSuchProcess:
        pass

    for ch in child_processes:
        try:
            ch.terminate()
            sleep(2)
            ch.kill()
            sleep(2)
            status = ch.status()
        except psutil.NoSuchProcess:
            pass

    try:
        process.terminate()
        sleep(2)
        process.kill()
        sleep(2)
        status = process.status()
    except psutil.NoSuchProcess:
        pass
