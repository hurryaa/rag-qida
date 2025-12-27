#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多用户隔离 AI 知识库助手 - FastAPI 后端

功能：
- 用户注册/登录（SQLite存储）
- 创建独立的 FastGPT 知识库
- 文件上传到用户知识库
- 基于知识库的对话功能（流式响应）

作者：AI Assistant
版本：1.0.0
"""

import os
import json
import sqlite3
import hashlib
import uuid
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
from contextlib import asynccontextmanager


# =============================================================================
# 环境变量配置
# =============================================================================

# 从环境变量读取配置，如果没有设置则使用默认值
FASTGPT_ADMIN_KEY = os.getenv("FASTGPT_ADMIN_KEY", "your-admin-key-here")
FASTGPT_CHAT_APP_KEY = os.getenv("FASTGPT_CHAT_APP_KEY", "your-chat-app-key-here")
FASTGPT_BASE_URL = os.getenv("FASTGPT_BASE_URL", "https://fastgpt.aiown.top")


# =============================================================================
# FastGPT API 端点
# =============================================================================
FASTGPT_CREATE_DATASET_URL = f"{FASTGPT_BASE_URL}/api/core/dataset/create"
FASTGPT_UPLOAD_FILE_URL = f"{FASTGPT_BASE_URL}/api/core/dataset/collection/create/localFile"
FASTGPT_CHAT_URL = f"{FASTGPT_BASE_URL}/api/v1/chat/completions"


# =============================================================================
# 应用生命周期管理 (使用现代 lifespan 方式)
# =============================================================================

def init_database():
    """
    初始化数据库，创建必要的表
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fastgpt_dataset_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_username ON users(username)
    ''')
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    init_database()
    print("应用启动完成")
    yield


# =============================================================================
# FastAPI 应用初始化
# =============================================================================
app = FastAPI(
    title="多用户隔离 AI 知识库助手",
    description="MVP: 每个用户拥有独立的 FastGPT 知识库，支持文件上传和智能对话",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置 CORS（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载前端静态文件
app.mount("/static", StaticFiles(directory="."), name="static")

# 安全认证
security = HTTPBasic()

# 数据库路径
DATABASE_PATH = "knowledge_base.db"


# =============================================================================
# 数据库操作
# =============================================================================

def get_db_connection():
    """
    获取 SQLite 数据库连接
    
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 支持列名访问
    return conn


def init_database():
    """
    初始化数据库，创建必要的表
    
    创建 users 表，包含：
    - id: 自增主键
    - username: 用户名
    - password: 密码（简单 hash）
    - fastgpt_dataset_id: 对应的 FastGPT 知识库 ID
    - created_at: 创建时间
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fastgpt_dataset_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引以提高查询效率
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_username ON users(username)
    ''')
    
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DATABASE_PATH}")


def hash_password(password: str) -> str:
    """
    简单密码 hash（生产环境应使用 bcrypt 等更安全的方式）
    
    Args:
        password: 原始密码
        
    Returns:
        str: hash 后的密码
    """
    # 使用 SHA256 + salt
    salt = "fastgpt-kb-mvp"  # 简单固定 salt，生产环境应随机生成
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        password: 原始密码
        hashed_password: hash 后的密码
        
    Returns:
        bool: 密码是否匹配
    """
    return hash_password(password) == hashed_password


def get_user_by_username(username: str) -> Optional[dict]:
    """
    根据用户名获取用户信息
    
    Args:
        username: 用户名
        
    Returns:
        dict 或 None: 用户信息字典，不存在则返回 None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return dict(user)
    return None


def create_user(username: str, password: str, fastgpt_dataset_id: str) -> dict:
    """
    创建新用户
    
    Args:
        username: 用户名
        password: 密码
        fastgpt_dataset_id: FastGPT 知识库 ID
        
    Returns:
        dict: 创建的用户信息
        
    Raises:
        HTTPException: 用户名已存在
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, password, fastgpt_dataset_id)
            VALUES (?, ?, ?)
        ''', (username, hash_password(password), fastgpt_dataset_id))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        return {
            "id": user_id,
            "username": username,
            "fastgpt_dataset_id": fastgpt_dataset_id
        }
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    finally:
        conn.close()


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> dict:
    """
    获取当前登录用户（依赖注入）
    
    Args:
        credentials: HTTP Basic 认证凭据
        
    Returns:
        dict: 用户信息
        
    Raises:
        HTTPException: 认证失败
    """
    user = get_user_by_username(credentials.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if not verify_password(credentials.password, user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return user


# =============================================================================
# FastGPT API 调用函数
# =============================================================================

def create_fastgpt_dataset(username: str) -> str:
    """
    调用 FastGPT API 创建知识库
    
    Args:
        username: 用户名（用于命名知识库）
        
    Returns:
        str: 创建的知识库 ID
        
    Raises:
        HTTPException: API 调用失败
    """
    headers = {
        "Authorization": f"Bearer {FASTGPT_ADMIN_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": f"{username}_KB",
        "type": "dataset",
        "parentId": None
    }
    
    try:
        response = requests.post(
            FASTGPT_CREATE_DATASET_URL,
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建知识库失败: {response.text}"
            )
        
        result = response.json()
        
        # FastGPT 返回格式: {"code": 200, "data": "dataset_id"}
        if result.get("code") == 200:
            return result.get("data")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建知识库失败: {result.get('message')}"
            )
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"网络请求失败: {str(e)}"
        )


async def upload_file_to_fastgpt(file: UploadFile, dataset_id: str) -> dict:
    """
    上传文件到 FastGPT 知识库
    
    Args:
        file: 上传的文件对象
        dataset_id: 目标知识库 ID
        
    Returns:
        dict: 上传结果
        
    Raises:
        HTTPException: 上传失败
    """
    headers = {
        "Authorization": f"Bearer {FASTGPT_ADMIN_KEY}"
    }
    
    # 构建上传数据
    data = {
        "datasetId": dataset_id,
        "parentId": "",
        "trainingType": "chunk",
        "chunkSize": 512,
        "metadata": json.dumps({})
    }
    
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 使用 requests 上传文件（FastGPT API 不支持 multipart/form-data 的异步版本）
        files = {
            "file": (file.filename, file_content, file.content_type or "application/octet-stream")
        }
        
        response = requests.post(
            FASTGPT_UPLOAD_FILE_URL,
            headers=headers,
            files=files,
            data={"data": data},
            timeout=60
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件上传失败: {response.text}"
            )
        
        result = response.json()
        
        if result.get("code") == 200:
            return {"success": True, "message": "文件上传成功", "data": result.get("data")}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件上传失败: {result.get('message')}"
            )
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"网络请求失败: {str(e)}"
        )


async def chat_with_fastgpt_stream(user_id: int, username: str, dataset_id: str, 
                                   message: str, chat_id: str):
    """
    与 FastGPT 进行流式对话
    
    Args:
        user_id: 用户 ID
        username: 用户名
        dataset_id: FastGPT 知识库 ID
        message: 用户消息
        chat_id: 会话 ID
        
    Yields:
        str: SSE 格式的数据块
    """
    headers = {
        "Authorization": f"Bearer {FASTGPT_CHAT_APP_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "chatId": chat_id,
        "stream": True,
        "detail": False,
        "variables": {
            "uid": str(user_id),
            "name": username,
            "fastdataUid": dataset_id  # 关键：指定用户的知识库
        },
        "messages": [{"role": "user", "content": message}]
    }
    
    try:
        # 发送请求到 FastGPT
        response = requests.post(
            FASTGPT_CHAT_URL,
            headers=headers,
            json=data,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            yield f"data: {json.dumps({'error': f'请求失败: {response.text}'})}\n\n"
            return
        
        # 逐块转发响应
        for line in response.iter_lines(decode_unicode=True):
            if line:
                # 处理 SSE 格式
                if line.startswith("data: "):
                    yield line + "\n\n"
                    
    except requests.exceptions.RequestException as e:
        yield f"data: {json.dumps({'error': f'网络请求失败: {str(e)}'})}\n\n"


# =============================================================================
# API 路由
# =============================================================================

# Pydantic 模型
class RegisterRequest(BaseModel):
    """用户注册请求模型"""
    username: str
    password: str


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    chat_id: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class ChatResponse(BaseModel):
    """聊天响应模型"""
    chat_id: str
    message: str


@app.get("/")
async def root():
    """
    根路径，返回前端页面
    """
    return FileResponse('index.html')


@app.post("/api/auth/register", response_model=dict)
async def register(request: RegisterRequest):
    """
    用户注册接口
    
    流程：
    1. 检查用户名是否已存在
    2. 调用 FastGPT API 创建知识库
    3. 将用户信息存入本地 SQLite
    4. 返回注册成功
    
    Args:
        request: 注册请求（用户名、密码）
        
    Returns:
        dict: 注册结果
        
    Raises:
        HTTPException: 用户名已存在或知识库创建失败
    """
    username = request.username.strip()
    password = request.password
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名和密码不能为空"
        )
    
    if len(username) < 3 or len(username) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名长度必须在 3-50 个字符之间"
        )
    
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度必须至少 6 个字符"
        )
    
    # 检查用户名是否已存在
    if get_user_by_username(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 调用 FastGPT API 创建知识库
    try:
        dataset_id = create_fastgpt_dataset(username)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识库失败: {str(e)}"
        )
    
    # 创建用户
    user = create_user(username, password, dataset_id)
    
    return {
        "success": True,
        "message": "注册成功",
        "user": user
    }


@app.post("/api/auth/login")
async def login(credentials: HTTPBasicCredentials = Depends(security)):
    """
    用户登录接口（HTTP Basic Auth）
    
    验证用户名和密码，返回用户信息和知识库 ID
    
    Args:
        credentials: HTTP Basic 认证凭据
        
    Returns:
        dict: 登录结果
        
    Raises:
        HTTPException: 认证失败
    """
    user = get_current_user(credentials)
    
    return {
        "success": True,
        "message": "登录成功",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "fastgpt_dataset_id": user["fastgpt_dataset_id"]
        }
    }


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    文件上传接口
    
    将用户上传的文件上传到其对应的 FastGPT 知识库
    
    Args:
        file: 上传的文件
        current_user: 当前登录用户
        
    Returns:
        dict: 上传结果
    """
    # 检查文件类型
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}。支持的类型: PDF, DOCX, TXT, MD"
        )
    
    # 获取用户的知识库 ID
    dataset_id = current_user["fastgpt_dataset_id"]
    
    # 上传到 FastGPT
    try:
        result = await upload_file_to_fastgpt(file, dataset_id)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}"
        )


@app.post("/api/chat")
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    聊天接口（流式响应）
    
    基于用户的知识库进行对话，支持 SSE 流式输出
    
    Args:
        request: 聊天请求
        current_user: 当前登录用户
        
    Returns:
        StreamingResponse: SSE 流式响应
    """
    message = request.message.strip()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息内容不能为空"
        )
    
    # 生成或使用指定的 chat_id
    chat_id = request.chat_id or str(uuid.uuid4())
    
    # 获取用户信息
    user_id = current_user["id"]
    username = current_user["username"]
    dataset_id = current_user["fastgpt_dataset_id"]
    
    # 生成 SSE 流
    return StreamingResponse(
        chat_with_fastgpt_stream(user_id, username, dataset_id, message, chat_id),
        media_type="text/event-stream"
    )


@app.get("/api/user/info")
async def get_user_info(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户信息
    
    Args:
        current_user: 当前登录用户
        
    Returns:
        dict: 用户信息
    """
    return {
        "success": True,
        "user": {
            "id": current_user["id"],
            "username": current_user["username"],
            "fastgpt_dataset_id": current_user["fastgpt_dataset_id"],
            "created_at": current_user["created_at"]
        }
    }


# =============================================================================
# 主程序入口
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
