# 单向发到飞书群

这个功能，主要是测试 pipeline 全流程畅通。单向发送的实用意义有限。

点击[创建飞书自定义机器人](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)，获取回调 WEBHOOK_URL，填写到 config.ini

```ini
# config.ini
..
[frontend]
type = "lark"
webhook_url = "${YOUR-LARK-WEBHOOK-URL}"
```

运行。结束后，技术助手的答复将**单向**发送到飞书群。

```shell
python3 -m huixiangdou.main
```

<img src="https://github.com/user-attachments/assets/80ea52ea-babf-4ded-8481-ded8a1ee9fd4" width="400">
