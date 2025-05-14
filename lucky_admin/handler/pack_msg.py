def pack_background_timed_task(msg: dict, start_time, task_name, cmd):
    """ 打包后台定时任务msg """
    msg['start_time'] = start_time
    msg['task_name'] = task_name
    msg['cmd'] = cmd
