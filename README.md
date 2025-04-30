# LinkSumm

LinkSumm是一款使用AI大模型驱动的智能摘要提取器，您可以输入一个URL地址，让AI为您总结内容。

## 主要特点

* 通过输入URL总结内容
* 支持接入多种AI大模型，只要兼容OpenAI API接口均可。
* 支持多种AI模型切换
* AI智能总结
* 支持流式传输
* 支持限制IP请求频率
* 支持限制输入字符串长度
* 支持请求SPA网页

## 安装

> 目前仅支持Docker安装，请确保您已经安装Docker和Docker Compose

新建`docker-compose.yaml`文件，内容如下：

```yaml
version: '3.8'

services:
  transmute:
    container_name: linksumm
    image: helloz/linksumm
    ports:
      - "2083:2083"
    restart: always
    volumes:
      - ./data:/opt/linksumm/app/data
```

然后输入`docker-compose up -d`启动。

## 使用

Transmute配置文件位于挂载目录下的`config/config.json`，使用标准的json格式：

```json
{
    "redis":{
        "host":"127.0.0.1",
        "port":6379,
        "password":"xxx",
        "db":0
    },
    "app":{
        "req_limit":100,
        "word_limit":3000
    },
    "site":{
        "title":"LinkSumm",
        "keywords":"",
        "description":"",
        "sub_title":""
    },
    "models":[
        {
            "base_url":"https://api.openai.com/v1",
            "model":"gpt-4o",
            "api_key":"sk-xxx",
            "name":"GPT-4o"
        }
    ]
}
```

需要修改`models`，添加您自己的AI大模型接口，大模型接口需要兼容OpenAI API格式，同时只需要路径的前缀部分，比如完整的API地址为：`https://api.openai.com/v1/chat/completions`，您只需要填写`https://api.openai.com/v1`，不需要末尾的`/chat/completions`，参数含义如下：

* `models.[0].base_url`：API前缀地址，不需要末尾的`/chat/completions`
* `models.[0].model`：模型参数值
* `models.[0].api_key`：密钥信息
* `models.[0].name`：前端显示的模型名称

可以在`models`节点下添加多个模型，比如：

```
"models":[
        {
            "base_url":"https://api.openai.com/v1",
            "model":"gpt-4o",
            "api_key":"sk-xxx",
            "name":"GPT-4o"
        },
        {
            "base_url":"https://api.deepseek.com/v1",
            "model":"deepseek-chat",
            "api_key":"sk-xxx",
            "name":"DeepSeek"
        }
    ]
```

**注意事项：**

1. 参数修改完毕后请务必校验json格式正确，否则可能导致程序异常
2. 修改参数后需要重启容器`docker restart linksumm`才会生效
3. 然后访问`http://IP:2083`测试

**其他参数**

* `app.req_limit`：单个访客请求频率限制，单位为24H，超出请求频率后将被限制
* `app.word_limit`：最大可输入的字符串长度
