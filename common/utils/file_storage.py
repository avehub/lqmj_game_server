import os
import uuid
import time
import mimetypes
from datetime import datetime
from typing import Dict, Optional, Tuple, BinaryIO, List, Union


from lucky_game.config.conf_start import ConfSrv


class FileStorageService:
    """文件存储服务"""

    def __init__(self):
        self.config = ConfSrv.FILE_UPLOAD
        self.upload_root = ConfSrv.UPLOAD_ROOT_PATH


    def get_file_extension(self, filename: str) -> str:
        """获取文件扩展名"""
        return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    def is_allowed_file(self, filename: str, file_type: Optional[str] = None) -> bool:
        """
        检查文件类型是否允许上传

        Args:
            filename: 文件名
            file_type: 文件类型(image/document/video/audio/archive)，如果为None则检查所有类型

        Returns:
            bool: 是否允许上传
        """
        ext = self.get_file_extension(filename)
        if not ext:
            return False

        if file_type:
            return ext in self.config.ALLOWED_EXTENSIONS.get(file_type, [])

        # 检查所有类型
        for allowed_exts in self.config.ALLOWED_EXTENSIONS.values():
            if ext in allowed_exts:
                return True

        return False

    def get_file_type(self, filename: str) -> Optional[str]:
        """根据文件名判断文件类型"""
        ext = self.get_file_extension(filename)
        if not ext:
            return None

        for file_type, extensions in self.config.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                return file_type

        return None

    def generate_filename(self, original_filename: str) -> str:
        """生成唯一文件名"""
        ext = self.get_file_extension(original_filename)
        random_name = uuid.uuid4().hex
        timestamp = int(time.time())

        if ext:
            return f"{random_name}_{timestamp}.{ext}"
        return f"{random_name}_{timestamp}"

    def get_storage_path(self, category: str, **kwargs) -> str:
        """
        获取存储路径

        Args:
            category: 存储类别(avatar/game/temp/document)
            **kwargs: 路径参数

        Returns:
            str: 存储路径
        """
        now = datetime.now()
        path_template = self.config.DIRECTORY_STRUCTURE.get(category, '{year}/{month}/{day}/')

        # 默认替换参数
        default_params = {
            'year': now.strftime('%Y'),
            'month': now.strftime('%m'),
            'day': now.strftime('%d')
        }

        # 合并自定义参数
        params = {**default_params, **kwargs}

        # 格式化路径
        path = path_template.format(**params)

        return path

    async def save_file(self, file_data: BinaryIO, filename: str, category: str = 'temp',
                        check_type: Optional[str] = None, **kwargs) -> Dict:
        """
        保存文件

        Args:
            file_data: 文件数据流
            filename: 原始文件名
            category: 存储类别
            check_type: 检查的文件类型
            **kwargs: 路径参数

        Returns:
            Dict: 保存结果
        """
        # 检查文件类型
        if check_type and not self.is_allowed_file(filename, check_type):
            return {
                'success': False,
                'message': f'不支持的文件类型: {filename}'
            }

        # 生成存储文件名和路径
        storage_filename = self.generate_filename(filename)
        relative_path = self.get_storage_path(category, **kwargs)
        full_path = os.path.join(relative_path, storage_filename)

        try:
             # 本地存储
            result = await self._save_to_local(file_data, relative_path, storage_filename)
            if not result['success']:
                return result

            file_url = self.config.LOCAL_STORAGE['public_url_prefix'].rstrip('/') + '/' + \
                       os.path.join(relative_path, storage_filename).replace('\\', '/')

            # 获取MIME类型
            mime_type, _ = mimetypes.guess_type(filename)

            return {
                'success': True,
                'filename': storage_filename,
                'original_filename': filename,
                'path': full_path,
                'url': file_url,
                'size': result.get('size', 0),
                'mime_type': mime_type,
                'category': category,
                'file_type': self.get_file_type(filename)
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'文件保存失败: {str(e)}'
            }

    async def _save_to_local(self, file_data: BinaryIO, relative_path: str, filename: str) -> Dict:
        """保存到本地存储"""
        # 创建目录
        full_dir = os.path.join(self.upload_root, relative_path)
        os.makedirs(full_dir, exist_ok=True)

        # 保存文件
        file_path = os.path.join(full_dir, filename)

        # 读取文件内容
        file_content = file_data.read()
        file_size = len(file_content)

        with open(file_path, 'wb') as f:
            f.write(file_content)

        return {
            'success': True,
            'path': file_path,
            'size': file_size
        }

    async def delete_file(self, file_path: str) -> Dict:
        """
        删除文件

        Args:
            file_path: 文件路径(相对路径)

        Returns:
            Dict: 删除结果
        """
        try:
            # 从本地删除

            full_path = os.path.join(self.upload_root, self.get_path_after_uploaded(file_path).lstrip('/'))
            separator = os.sep  # Windows: '\', Linux/macOS: '/'
            if separator == '\\':
                full_path = full_path.replace('/', '\\')
            if os.path.exists(full_path):
                os.remove(full_path)
                return {'success': True, 'message': '文件删除成功'}
            else:
                return {'success': False, 'message': '文件不存在'}
        except Exception as e:
            return {'success': False, 'message': f'删除文件失败: {str(e)}'}

    def get_path_after_uploaded(self, file_url):
        return file_url.split(ConfSrv.RESOURCE_CHAIN_PATH, 1)[1] if ConfSrv.RESOURCE_CHAIN_PATH in file_url else ""

    async def get_file_info(self, file_path: str) -> Dict:
        """
        获取文件信息

        Args:
            file_path: 文件路径(相对路径)

        Returns:
            Dict: 文件信息
        """
        try:
            # 从本地获取信息
            full_path = os.path.join(self.upload_root, file_path.lstrip('/'))
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                mime_type, _ = mimetypes.guess_type(full_path)
                last_modified = os.path.getmtime(full_path)

                return {
                    'success': True,
                    'exists': True,
                    'size': file_size,
                    'mime_type': mime_type,
                    'last_modified': last_modified,
                    'url': self.config.LOCAL_STORAGE['public_url_prefix'].rstrip('/') + '/' + file_path.lstrip('/')
                }
            else:
                return {'success': False, 'exists': False, 'message': '文件不存在'}
        except Exception as e:
            return {'success': False, 'message': f'获取文件信息失败: {str(e)}'}


# 创建单例
file_storage = FileStorageService()
