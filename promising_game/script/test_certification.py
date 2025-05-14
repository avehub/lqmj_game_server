import asyncio

from common.utils.tool_certification import do_shi_ming_query, do_shi_ming_check, do_shi_ming_update

if __name__ == '__main__':
    # asyncio.run(do_shi_ming_check("张富进", 522322199611281331, 1000109, "F4qnR7"))
    # asyncio.run(do_shi_ming_query("100000000000000001", "F4qnR7"))
    index = 1
    hui_hua_id = 1
    offline = 0
    is_guest = 0
    dev_mark = "xxxxx"  # 设备标识
    pi = "1fffbjzos82bs9cnyj1dna7d6d29zg4esnh99u"
    test_code = "GWRXcm"
    asyncio.run(do_shi_ming_update(index, hui_hua_id, offline, is_guest, dev_mark, pi, test_code))
