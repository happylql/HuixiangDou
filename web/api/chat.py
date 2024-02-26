from fastapi import APIRouter, Request, Response, Depends

from web.middleware.token import check_hxd_token
from web.model.chat import ChatRequestBody, ChatOnlineResponseBody
from web.model.qalib import QalibInfo
from web.service.chat import ChatService

chat_api = APIRouter()


@chat_api.post("/v1/online")
async def chat_online(request: Request, response: Response, body: ChatRequestBody,
                      hxd_info: QalibInfo = Depends(check_hxd_token)):
    return await ChatService(request, response, hxd_info).chat_online(body)


@chat_api.post("/v1/onlineResponse")
async def chat_online_response(request: Request, response: Response, body: ChatOnlineResponseBody,
                               hxd_info: QalibInfo = Depends(check_hxd_token)):
    return await ChatService(request, response, hxd_info).fetch_response(body)
