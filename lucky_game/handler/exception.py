import traceback
from typing import Union
from dataclasses import dataclass

from sanic import Request, response
from nsanic.libs.manager import HeaderSet
from nsanic.libs.rds_client import RdsError
from nsanic.exception import JsonFinish
from http import HTTPStatus
from common.public.enum_const import StaCode


@dataclass
class RealJsonFinish(Exception):
    """完成请求状态异常"""
    code: StaCode
    '''状态码'''
    data: Union[dict, list, str, int, float] = None
    '''响应数据'''
    total: int = 0
    '''针对于分页数据响应的总数量'''
    hint: str = ''
    '''响应消息提示'''
    headers: dict = None
    '''附加响应头'''


class RCatchExpt():
    conf = None

    __code_map = {
        400: '请求结构错误,无法解析的结构',
        404: 'API接口不存在',
        500: '出错啦，请稍后再试或联系管理员检查',
        403: '请求结构不支持'
    }

    @classmethod
    def set_conf(cls, conf):
        cls.conf = conf

    @classmethod
    def __log_err_info(cls, req: Request, err_info: str):
        log_info = f"请求异常信息:\n接口--{req.path}\n方法--{req.method}\n头部--{req.headers.items()}\nquery参数--{req.args}\nbody--{str(req.body, 'utf8')}\n错误信息--{err_info}"
        if cls.conf.DEBUG_MODE:
            return print(log_info)
        cls.conf.log.error(log_info)

    @classmethod
    def catch_req(cls, req: Request, expt):
        print(req.args.get)
        req_id = req.headers.get('req_id')
        req_id and cls.conf.rds and cls.conf.rds.drop_item(f"{cls.conf.PROCESSING_REQ}:{req_id}")
        headers = HeaderSet.out(cls.conf)
        hasattr(expt, 'headers') and expt.headers and headers.update(expt.headers)
        # if isinstance(expt, RdsError):
        #     data = PbBaseRep.encode(code=500, msg='Invalid Cache Server. Please contact administrator.')
        #     return response.json(data, status=500, headers=headers)
        if isinstance(expt, JsonFinish):
            body = {'code': expt.code.val, 'data': expt.data, 'msg': expt.hint or expt.code.msg}
            return response.json(body, status=expt.code.http, headers=headers)
        if hasattr(expt, 'status_code'):
            enum_code = HTTPStatus._value2member_map_.get(expt.status_code)
            if not enum_code:
                hint = cls.__code_map.get(expt.status_code) or ""
            else:
                hint = enum_code.phrase
            if expt.status_code == 500:
                cls.__log_err_info(req, traceback.format_exc())

            data = {'code': expt.status_code, 'msg': hint}
            return response.json(data, status=expt.status_code, headers=headers)
        cls.__log_err_info(req, traceback.format_exc())
        data = {'code': 500, 'msg': 'There are some error, please connect administrator to check.'}
        return response.json(data, status=500)
