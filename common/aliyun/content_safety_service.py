import base64
import logging
import json
import os
from typing import Dict, Any, Union, List, Tuple

from alibabacloud_green20220302.client import Client as GreenClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_green20220302 import models as green_models
from alibabacloud_tea_util import models as util_models
from common.public.conf import AliYunContentSafetyConf, SERVER_ADDR

logger = logging.getLogger(__name__)


class ContentSafetyService:
    def __init__(self):
        config = open_api_models.Config(
            access_key_id=AliYunContentSafetyConf.ACCESS_KEY_ID,
            access_key_secret=AliYunContentSafetyConf.ACCESS_KEY_SECRET,
            region_id=AliYunContentSafetyConf.REGION_ID,
            endpoint=AliYunContentSafetyConf.ENDPOINT,
            # 连接时超时时间，单位毫秒（ms）。
            connect_timeout=3000,
            # 读取时超时时间，单位毫秒（ms）。
            read_timeout=6000,
        )
        self.client = GreenClient(config)

    async def scan_image(self, image_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Scan an image file for inappropriate content

        Args:
            image_path: Path to the image file

        Returns:
            Tuple containing:
            - Boolean indicating if the image passed security checks
            - Dictionary with detailed scan results
        """
        try:
            # Read image file and encode it
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')

            # Prepare request
            task = {
                "dataId": os.path.basename(image_path),
                "content": base64_image
            }

            runtime = util_models.RuntimeOptions()
            request = green_models.ImageModerationRequest(
                service="baselineCheck",
                service_parameters=json.dumps({
                    "bizType": "default",
                    "scenes": AliYunContentSafetyConf.IMAGE_SCAN_SCENES,
                    "tasks": [task]
                })
            )

            # Call the API
            response = self.client.image_moderation_with_options(request, runtime)

            # Process response
            result = json.loads(response.body.data)

            # Check if any violations were found
            passed = True
            details = {"violations": []}

            if "results" in result and result["results"]:
                for scene_result in result["results"]:
                    for scene_data in scene_result.get("results", []):
                        scene = scene_data.get("scene")
                        suggestion = scene_data.get("suggestion")
                        confidence = scene_data.get("rate", 0) * 100

                        # If the confidence exceeds our threshold, mark as violation
                        if (suggestion == "block" or
                                (suggestion == "review" and confidence >= AliYunContentSafetyConf.CONFIDENCE_THRESHOLD)):
                            passed = False
                            details["violations"].append({
                                "scene": scene,
                                "confidence": confidence,
                                "suggestion": suggestion
                            })

            details["raw_result"] = result
            return passed, details

        except Exception as e:
            # In case of errors, log the exception and default to failing closed
            # This is safer than allowing potentially harmful content through
            return False, {"error": str(e), "violations": [{"scene": "error", "suggestion": "block"}]}

    async def scan_url(self, image_url: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Scan an image URL for inappropriate content

        Args:
            image_url: URL of the image to scan

        Returns:
            Tuple containing:
            - Boolean indicating if the image passed security checks
            - Dictionary with detailed scan results
        """
        try:
            # Prepare request
            print(image_url)
            runtime = util_models.RuntimeOptions()
            request = green_models.ImageModerationRequest(
                service="baselineCheck",
                service_parameters=json.dumps({
                    "dataId": image_url[-36:-4],
                    "imageUrl": SERVER_ADDR + image_url
                })
            )
            # Call the API
            response = self.client.image_moderation_with_options(request, runtime)
            print("response:", response)
            # Process response
            result = json.loads(response.body.data)
            print("result:", result)
            # Check if any violations were found
            passed = True
            details = {"violations": []}

            if "results" in result and result["results"]:
                for scene_result in result["results"]:
                    for scene_data in scene_result.get("results", []):
                        scene = scene_data.get("scene")
                        suggestion = scene_data.get("suggestion")
                        confidence = scene_data.get("rate", 0) * 100

                        # If the confidence exceeds our threshold, mark as violation
                        if (suggestion == "block" or
                                (suggestion == "review" and confidence >= AliYunContentSafetyConf.CONFIDENCE_THRESHOLD)):
                            passed = False
                            details["violations"].append({
                                "scene": scene,
                                "confidence": confidence,
                                "suggestion": suggestion
                            })

            details["raw_result"] = result
            return passed, details

        except Exception as e:
            print("e:", str(e))
            # In case of errors, log the exception and default to failing closed
            return False, {"error": str(e), "violations": [{"scene": "error", "suggestion": "block"}]}


content_security = ContentSafetyService()
