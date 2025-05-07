from app.api.summ import Summ
from app.api.html import Html
from fastapi import APIRouter

# 创建 APIRouter 实例
router = APIRouter()


html = Html()
summ = Summ()


router.get("/api/get/models")(summ.get_models)
# 通过URL获取页面内容
router.post("/api/get/content")(summ.extract_content)
# 通过传递HTML提取内容
router.post("/api/get/html2md")(summ.html_to_md)
router.post("/api/summ")(summ.chat)
router.get("/")(html.index)
