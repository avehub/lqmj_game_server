import asyncio
import time
import traceback
import random


def handle_task_result(task):
    """ 回调函数捕获异常 """
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        # 在终端中直接打印异常
        raise e


class Delay:
    """延迟对象
    """

    def __init__(self, f, *args, **kw):
        self.f = f
        self.args = args
        self.kw = kw
        self.log_handler = kw.pop("log_handler", None)

    async def call(self):
        """ 返回一个协程，所以外部可以用await等待 """
        # 直接调用函数，允许异常自然抛出
        try:
            if asyncio.iscoroutinefunction(self.f):
                return await self.f(*self.args, **self.kw)
            else:
                return self.f(*self.args, **self.kw)
        except Exception:
            _str = f"延时调用错误：{self.f.__name__}, {traceback.format_exc()}"
            self.log_handler(_str) if self.log_handler else print(_str)


class DelayCall():
    """以一个微线程的方式实现一个延时调用
    接受普通函数或者协程函数
    example:
    def p(x):
        print x
    d = DelayCall(5, p, "xx")
    d.start()
    """
    __slots__ = (
        "seconds",
        "delay",
        "task",
        "__start_seconds",
        "__current_delay"
    )

    def __init__(self, seconds, f, *args, **kw):
        if isinstance(seconds, tuple) and len(seconds) == 2:
            assert 0 <= seconds[0] <= seconds[1], "seconds range must be valid"
        else:
            assert seconds >= 0, "seconds must be greater than or equal to 0"
        self.task = None
        self.seconds = seconds
        self.delay = Delay(f, *args, **kw)
        self.__start_seconds = 0
        self.__current_delay = 0

    def cancel(self):
        """
        取消延时调用
        cancel self可能会影响主流程
        """
        if self.task and not self.task.done():
            print(f"task被取消：{self.delay.f.__name__}")
            self.task.cancel()

    def left_seconds(self):
        """ 获取计时器的剩余时间 """
        if not self.__start_seconds:
            return self.seconds[0] if isinstance(self.seconds, tuple) else self.seconds
        return int(max(0.0, self.__current_delay - (time.time() - self.__start_seconds)))

    async def delay_call(self):
        # 计算实际延迟时间
        self.__current_delay = random.randint(*self.seconds) if isinstance(self.seconds, tuple) else self.seconds
        await asyncio.sleep(self.__current_delay)
        # 直接调用并允许异常抛出
        return await self.delay.call()

    def start(self):
        """ 创建一个task """
        self.__start_seconds = time.time()
        self.__current_delay = random.randint(*self.seconds) if isinstance(self.seconds, tuple) else self.seconds
        print(f"新启动延时调用：{self.delay.f.__name__}, {self.__current_delay}秒后执行")
        self.task = asyncio.create_task(self.delay_call())
        return self.task

    def loop_start(self):
        self.task = asyncio.create_task(self.__loop_call())
        return self.task

    async def __loop_call(self):
        """ 循环调用 """
        while 1:
            await self.delay_call()


async def delay_func(seconds, func, *args, **kwargs):
    """
    延时调用func
    func: 协程或普通函数
    """
    if not isinstance(seconds, (int, float, tuple)) or (isinstance(seconds, tuple) and (len(seconds) != 2 or seconds[0] < 0 or seconds[1] < seconds[0])):
        raise ValueError("warp_func seconds error !!!")
    delay_time = random.randint(*seconds) if isinstance(seconds, tuple) else seconds
    await asyncio.sleep(delay_time)
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)
