import io
from typing import List, Optional

from lucky_game.base_api import GameAuthApi
from sanic import Request
from tortoise.exceptions import DoesNotExist
from lucky_game.config.conf_start import ConfSrv
from common.utils.file_storage import file_storage
from common.public.enum_const import StaCode
from common.public.conf import SERVER_ADDR


class FileUploadHandler(GameAuthApi):
    """文件上传处理器"""
    async def _handle_file_upload(self, files, category, check_type=None, **kwargs):
        """处理文件上传"""
        results = []
        for file_info in files:
            field_name = file_info.get('field_name', 'file')
            filename = file_info.get('filename', '')
            content_type = file_info.get('content_type', '')
            body = file_info.get('body', b'')

            if not filename or not body:
                results.append({
                    'success': False,
                    'file_url': field_name,
                    'message': '文件名或内容为空'
                })
                continue

            # 检查文件大小
            file_size = len(body)
            if file_size > ConfSrv.FILE_UPLOAD.MAX_FILE_SIZE:
                results.append({
                    'success': False,
                    'file_url': field_name,
                    'message': f'文件大小超过限制: {file_size} > {ConfSrv.FILE_UPLOAD.MAX_FILE_SIZE} 字节'
                })
                continue

            # 创建内存文件对象
            file_obj = io.BytesIO(body)

            # 保存文件
            save_result = await file_storage.save_file(
                file_obj,
                filename,
                category=category,
                check_type=check_type,
                **kwargs
            )

            if save_result['success']:
               results.append({
                   'success': True,
                   'file_url': SERVER_ADDR + save_result.get('url'),
                   'message': '上传成功',
               })
        return True, results

    async def post(self, req: Request, **kwargs):
        """上传文件"""
        content_type = req.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            return False, '无效的请求类型，必须是multipart/form-data'

        # 解析请求参数
        files = req.files.get("files")
        if not files:
            return False, '未找到上传的文件'
        category = req.form.get('category', 'temp')
        check_type = req.form.get('check_type')  # 可选的文件类型检查

        # 构造额外参数
        extra_params = {}
        for key, value in req.form.items():
            if key not in ['category', 'check_type']:
                extra_params[key] = value[0] if len(value) > 0 else None

        # 处理文件上传
        file_info_list = []
        file_info = {
            'field_name': files.name,
            'filename': files.name,
            'content_type': files.type,
            'body': files.body
        }
        file_info_list.append(file_info)
        if not files:
            return self.answer(StaCode.FAIL, hint="未找到上传的文件")

        # 处理文件上传
        sta, results = await self._handle_file_upload(file_info_list, category, check_type, **extra_params)
        if sta is False:
            return self.answer(StaCode.FAIL, data=results, hint="上传失败")
        return self.answer(data=results)


class FileDeleteHandler(GameAuthApi):
    async def post(self, req: Request, **kwargs):
        """删除文件"""
        file_url = req.json.get("file_url")
        if not file_url:
            return self.answer(StaCode.FAIL, hint="未找到需要删除的文件")
        file_path = file_url
        try:
            # 从存储中删除
            delete_result = await file_storage.delete_file(file_path)
            if delete_result['success']:
                return self.answer()
            else:
                return self.answer(StaCode.FAIL, hint=delete_result['message'])
        except DoesNotExist:
            return self.answer(StaCode.FAIL, hint="文件不存在")
