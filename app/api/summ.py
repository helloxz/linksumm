import trafilatura
from playwright.async_api import async_playwright
from fastapi import Request, HTTPException
from app.utils.helper import show_json
from pydantic import BaseModel
from datetime import datetime
import re
import asyncio
from trafilatura import extract, extract_metadata
from openai import OpenAI
import json
from fastapi.responses import StreamingResponse
import os
from fastapi import Form
import random
import httpx
from typing import Optional

class UrlItem(BaseModel):
    url: str
# 声明需要的参数
class InputItem(BaseModel):
    model: str
    input: str

class Summ:
    modelList = []
    def __init__(self):
        # 获取当前工作路径
        current_path = os.getcwd()
        # 打印当前路径
        # print("当前路径:", current_path)
        # 从配置文件中获取模型列表
        with open('app/data/config/config.json', 'r') as file:
            data = json.load(file)

        self.modelList = data["models"]

        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
        ]


    # AI总结接口
    async def chat(self,item:InputItem,request: Request = None):
        # 解析json数据
        model = item.model
        input = item.input
        
        # 判断模型是否存在
        modelInfo = self._is_support_model(model)
        if not modelInfo:
            return show_json(400, "The model does not exist", None)
        
        # print("modelInfo:", modelInfo)
        word_limit = request.app.state.config["app"]["word_limit"]
        # 判断内容长度，必须2到1000个字符之间 
        if len(input) < 2 or len(input) > word_limit:
            return show_json(400, f'The content length must be between 2 and {word_limit} characters', None)
        
        
        # 设置提示词
        prompt = f"""
你是一个内容总结助手。无论输入的什么语言，最后都用中文返回。请按照以下步骤处理我提供的文本内容：


 **内容总结**：
   - 写出一段**核心摘要**，概括全文的主要内容。
   - 提取出**关键要点列表**，每条要点清晰简洁，突出重要信息，最多10条。

请严格按照上述顺序输出结果，不要添加额外解释或格式。
"""


        # 初始化客户端
        client = OpenAI(
            api_key=modelInfo["api_key"],  # 替换为你的密钥
            base_url=modelInfo["base_url"]  # 替换为你的地址
        )

        def generate():
            stream = client.chat.completions.create(
                model=modelInfo["model"],
                temperature=0.5,
                messages=[
                    {"role": "assistant", "content": prompt},
                    {
                        "role": "user",
                        "content": f"<<<{input}>>>",
                    }
                ],
                stream=True  # 启用流式输出
            )
            
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    content = chunk.choices[0].delta.content
                    
                    # print(content)
                    if content is not None:
                        value = {
                            "value": content
                        }
                        
                        
                        # 按照SSE格式发送数据
                        # yield f"data: {content}\n\n"
                        # 使用json.dumps将字典转换为JSON格式的字符串
                        yield f"data: {json.dumps(value)}\n\n"
        
            yield f"data: [DONE]\n\n"
        
        # 请求次数+1
        await self._add_req_count(request)

        # 写入日志
        """
        asyncio.create_task(add_document_to_zincsearch({
            "ip": get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "input": input,
            "output": self.output,
            "target_lang": target_language,
            "model": model,
            "browser_lang": browser_lang
        }))
        """
        # 返回流式响应
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    # 检查模型是否存在
    def _is_support_model(self,model: str):
        # 如果模型为auto
        if model == "auto":
            # 直接使用第一个模型
            return self.modelList[0]
            
        # 模型不为空，遍历模型列表
        for modelInfo in self.modelList:
            if modelInfo["model"] == model:
                return modelInfo
            
        # 如果不存在，返回False
        return False
    # 提取内容接口
    async def extract_content(
            self,
            url:str=Form(...),
            mode: str = Form("fast"),  # 默认"fast"
            request: Request = None
    ):
        try:
            # 检查URL是否有效
            if not url or not url.startswith(('http://', 'https://')):
                return show_json(400, "Invalid URL format", None)

            # 检查URL长度
            if len(url) > 2000:
                return show_json(400, "URL is too long", None)

            # 爬取HTML内容
            if mode == "deep":
                # 使用Playwright爬取渲染后的HTML内容
                html_content = await self._fetch_html(url)
            else:
                # 使用httpx快速爬取HTML内容
                html_content = await self._fast_fetch_html(url)
                # 打印内容
                # print(html_content)
            # html_content = await self._fetch_html(url)
            if not html_content:
                return show_json(404, "Failed to fetch content from URL", None)

            # 提取内容
            result = await self._extract_with_trafilatura(html_content, url)
            
            # 记录请求次数
            if request:
                await self._add_req_count(request)
                
            return show_json(200, "Content extracted successfully", result)
            
        except Exception as e:
            return show_json(500, f"Error processing URL: {str(e)}", None)
    
    async def _fetch_html(self, url: str) -> str:
        """使用Playwright爬取渲染后的HTML内容"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                
                # 创建一个新的浏览器上下文，设置用户代理
                import random
                user_agent = random.choice(self.user_agents)
                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1920, "height": 1080},
                    device_scale_factor=1.0,
                    # 拦截图片、样式表等非必要资源
                    bypass_csp=True,
                )

                # 启用资源拦截
                await context.route("**/*", lambda route: (
                    route.abort() 
                    if route.request.resource_type in {"image", "stylesheet", "font", "media"} 
                    else route.continue_()
                ))
                
                # 添加额外的头信息模拟真实浏览器
                await context.set_extra_http_headers({
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                    "Cache-Control": "max-age=0",
                    "Sec-Ch-Ua": '"Chromium";v="121", "Not A(Brand";v="99"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                })
                
                page = await context.new_page()
                
                # 设置页面加载超时时间为20s
                page.set_default_timeout(20000)
                
                # 随机等待一会儿，避免被识别为爬虫
                await asyncio.sleep(1)
                
                await page.goto(url, wait_until="networkidle")
                
                # 滚动页面，触发懒加载内容
                await page.evaluate("""
                    window.scrollTo(0, document.body.scrollHeight / 3);
                    new Promise(r => setTimeout(r, 500));
                    window.scrollTo(0, document.body.scrollHeight * 2 / 3);
                    new Promise(r => setTimeout(r, 500));
                    window.scrollTo(0, document.body.scrollHeight);
                """)
                
                # 等待一会儿，让动态内容加载完成
                await asyncio.sleep(2)
                
                html = await page.content()
                await context.close()
                await browser.close()
                
                return html
                
        except Exception as e:
            print(f"Error fetching HTML: {str(e)}")
            return ""
        
    # 使用httpx更快速的请求
    async def _fast_fetch_html(self, url: str) -> str:
        """使用httpx爬取HTML内容，模拟浏览器行为"""
        try:
            # 随机选择一个用户代理
            user_agent = random.choice(self.user_agents)
            
            # 配置请求头，模拟真实浏览器
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Chromium";v="121", "Not A(Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "Connection": "keep-alive",
                "Referer": "https://www.google.com/",  # 模拟从Google跳转
            }
            
            # 配置客户端选项
            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10
            )
            
            # 使用异步客户端
            async with httpx.AsyncClient(
                headers=headers,
                limits=limits,
                timeout=10.0,  # 20秒超时
                follow_redirects=True,  # 跟随重定向
                http2=True,  # 启用HTTP/2
            ) as client:
                # 发送请求
                response = await client.get(
                    url,
                    # 模拟浏览器cookie
                    cookies={"session": str(random.randint(1000, 9999))},
                    # 添加随机查询参数，避免缓存
                    params={"_t": str(random.randint(100000, 999999))}
                )
                
                response.raise_for_status()  # 检查HTTP错误
                
                # 返回HTML内容
                return response.text
                
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error occurred: {e.response.status_code}")
        except httpx.RequestError as e:
            raise Exception(f"Request error occurred: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
    
    async def _extract_with_trafilatura(self, html: str, url: str) -> dict:
        """使用Trafilatura提取正文内容并转换为Markdown"""
        try:
            # 提取正文内容
            extracted = trafilatura.extract(
                html,
                output_format="markdown",
                include_images=False,# 禁用图片提取
                include_links=False,# 禁用链接提取
                date_extraction_params={"extensive_search": False}
            )

            # 提取元数据（title, date 等）
            metadata = trafilatura.extract_metadata(html)
            
            title = ""
            date = ""

            if metadata:
                title = metadata.title or ""
                date = metadata.date or ""
            # 提取日期
            # date = trafilatura.extract_metadata(html, url).get('date', '')
            # if date:
            #     try:
            #         # 尝试格式化日期
            #         date_obj = datetime.fromisoformat(date.replace('Z', '+00:00'))
            #         date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            #     except (ValueError, TypeError):
            #         # 如果格式化失败，保持原样
            #         pass
            
            # 处理内容中的图片链接，确保它们是绝对URL
            if extracted:
                # 将相对链接转换为绝对链接
                base_url = re.match(r'(https?://[^/]+)', url).group(1)
                path_base = '/'.join(url.split('/')[:-1]) + '/'
                
                def replace_relative_url(match):
                    img_url = match.group(1)
                    if img_url.startswith('/'):
                        return f'![Image]({base_url}{img_url})'
                    elif not img_url.startswith(('http://', 'https://')):
                        return f'![Image]({path_base}{img_url})'
                    return f'![Image]({img_url})'
                
                extracted = re.sub(r'!\[Image\]\(([^)]+)\)', replace_relative_url, extracted)

            # 替换v2ex中不需要的内容
            to_remove = "**V2EX = way to explore**V2EX 是一个关于分享和探索的地方\n\n"
            extracted = extracted.replace(to_remove, "")
            
            # 构建返回结果
            result = {
                "title": title,
                "content": extracted if extracted else "No content could be extracted",
                "date": date if date else "",
                "url": url
            }
            
            return result
            
        except Exception as e:
            print(f"Error in Trafilatura extraction: {str(e)}")
            return {
                "title": "",
                "content": "Error extracting content",
                "date": "",
                "url": url
            }
    
    # 请求次数+1
    async def _add_req_count(self, request: Request):
        # 生成key
        # 获取当前日期并格式化为 YYYYMMDD
        current_date = datetime.now().strftime('%Y%m%d')
        # 从request中获取IP
        from app.utils.helper import get_client_ip
        ip = get_client_ip(request)
        key = "linksumm:" + current_date + ":" + ip
        await request.app.state.redis.incr(key)
        # 设置过期时间为24小时
        await request.app.state.redis.expire(key, 24 * 60 * 60)

    # 获取模型列表
    async def get_models(self,request:Request):
        newModelList = []
        # 遍历并去除敏感数据
        for model in self.modelList:
            newModelList.append({
                "model": model["model"],
                "name": model["name"]
            })
        return show_json(200, "success", newModelList)
    
    # 获取html内容，然后提取为markdown内容
        # 获取html内容，然后提取为markdown内容
    async def html_to_md(
        self,
        html: str = Form(...),
        url: str = Form(default="https://example.com")  # 提供默认值，因为_extract_with_trafilatura需要url参数
    ):
        try:
            # 检查HTML是否为空
            if not html or len(html.strip()) == 0:
                return show_json(400, "HTML content cannot be empty", None)
            
            # 简单验证是否是HTML内容
            # 检查是否包含基本HTML标签
            if not re.search(r'<\s*html.*?>|<\s*body.*?>|<.*?>', html, re.IGNORECASE):
                return show_json(400, "Invalid HTML format", None)
            
            # 提取内容
            result = await self._extract_with_trafilatura(html, url)
            
            return show_json(200, "Content extracted successfully", result)
            
        except Exception as e:
            return show_json(500, f"Error processing HTML: {str(e)}", None)

