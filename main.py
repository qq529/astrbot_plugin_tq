import astrbot
from astrbot import CommandSession
import aiohttp
import asyncio
from typing import Dict, Optional


# 注册插件
@astrbot.plugin_registry.register(
    name="天气查询插件",
    desc="根据城市名称查询实时天气信息",
    version="1.0.0",
    author="YourName"
)
class WeatherPlugin:
    """天气查询插件
    
    提供城市天气查询功能，使用异步aiohttp进行网络请求
    符合AstrBot插件开发规范
    """
    
    def __init__(self):
        # API接口地址
        self.api_url = "https://api.suyanw.cn/api/xztq.php"
        # 错误码映射表
        self.error_messages = {
            400: "请求错误！",
            403: "请求被服务器拒绝！",
            405: "客户端请求的方法被禁止！",
            408: "请求时间过长！",
            500: "服务器内部出现错误！",
            501: "服务器不支持请求的功能，无法完成请求！",
            503: "系统维护中！"
        }
    
    @astrbot.event_listener.on_command(cmd="天气", alias={"tq", "weather"})
    async def weather_query(self, session: CommandSession):
        """天气查询命令处理函数
        
        Args:
            session: 命令会话对象
        """
        # 获取用户输入的城市名
        city_name = session.get_param("city_name")
        
        # 如果未提供城市名，提示用户输入
        if not city_name:
            await session.send("请问您要查询哪个城市的天气呢？")
            city_name = await session.aget(
                param_name="city_name", 
                prompt="请直接告诉我城市名："
            )
            if not city_name:
                await session.send("未收到城市名，查询已取消。")
                return
        
        try:
            # 获取天气数据
            result = await self._get_weather_async(city_name)
            
            if result["success"]:
                # 解析天气数据
                parsed_data = self._parse_weather_data(result["data"])
                if parsed_data:
                    # 构建回复消息
                    reply_msg = self._build_weather_message(city_name, parsed_data)
                    await session.send(reply_msg)
                else:
                    await session.send(f"抱歉，未能解析{city_name}的天气数据。")
            else:
                await session.send(f"查询失败: {result['error']}")
                
        except Exception as e:
            # 良好的错误处理，防止插件崩溃
            await session.send(f"天气查询过程中出现异常，请稍后重试。错误信息: {str(e)}")
    
    async def _get_weather_async(self, city_name: str) -> Dict:
        """异步获取天气数据
        
        使用aiohttp替代requests，符合AstrBot开发规范
        
        Args:
            city_name: 城市名称
            
        Returns:
            包含天气数据的字典
        """
        params = {"msg": city_name}
        
        try:
            # 使用aiohttp进行异步HTTP请求
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(self.api_url, params=params) as response:
                    
                    if response.status == 200:
                        data = await response.text()
                        return {
                            "success": True,
                            "data": data,
                            "status_code": response.status
                        }
                    else:
                        error_msg = self.error_messages.get(
                            response.status, 
                            f"未知错误: {response.status}"
                        )
                        return {
                            "success": False,
                            "error": error_msg,
                            "status_code": response.status
                        }
                        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "请求超时，请稍后重试",
                "status_code": None
            }
        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": f"网络请求异常: {str(e)}",
                "status_code": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"未知错误: {str(e)}",
                "status_code": None
            }
    
    def _parse_weather_data(self, raw_data: str) -> Optional[Dict]:
        """解析天气数据
        
        Args:
            raw_data: 原始返回数据
            
        Returns:
            解析后的天气信息字典，解析失败返回None
        """
        try:
            lines = raw_data.strip().split('\n')
            weather_info = {}
            
            for line in lines:
                # 跳过空行和图片链接行
                if not line.strip() or '`#img=' in line:
                    continue
                    
                # 解析数据行
                if '：' in line:
                    # 去除行号（如 "02. "）
                    cleaned_line = line.split('. ', 1)[-1] if '. ' in line else line
                    
                    # 分割键值对
                    if '：' in cleaned_line:
                        key, value = cleaned_line.split('：', 1)
                        weather_info[key.strip()] = value.strip()
            
            return weather_info if weather_info else None
            
        except Exception:
            # 解析过程中出现异常，返回None
            return None
    
    def _build_weather_message(self, city_name: str, weather_data: Dict) -> str:
        """构建天气消息
        
        Args:
            city_name: 城市名称
            weather_data: 天气数据字典
            
        Returns:
            格式化的天气消息字符串
        """
        try:
            city = weather_data.get('城市名', city_name)
            weather = weather_data.get('实时天气', '未知')
            temperature = weather_data.get('实时气温', '未知')
            update_time = weather_data.get('更新时间', '未知')
            detail_location = weather_data.get('详细地名', '')
            
            message = f"🌤️ {city}天气信息\n"
            message += f"📍 位置: {detail_location}\n" if detail_location else ""
            message += f"🌡️ 气温: {temperature}\n"
            message += f"☁️ 天气: {weather}\n"
            message += f"🕒 更新: {update_time}"
            
            return message
            
        except Exception:
            # 构建消息过程中出现异常，返回简单提示
            return f"{city_name}的天气信息获取成功，但格式解析异常。"