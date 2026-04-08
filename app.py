import streamlit as st
import requests
import json
import time
from typing import Dict, List, Optional
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# ===================== 本地法律数据库 =====================
class LocalLawDatabase:
    """本地法律数据库，包含常用法律条文"""
    
    def __init__(self):
        self.laws = {
            "民法典": {
                "name": "中华人民共和国民法典",
                "url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgwODE3MzI3MjA1MzAxNzM0NzU0ODA0MjI0MDE",
                "articles": {
                    "侵权责任": "第1165条：行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。",
                    "合同违约": "第577条：当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。",
                    "离婚冷静期": "第1077条：自婚姻登记机关收到离婚登记申请之日起三十日内，任何一方不愿意离婚的，可以向婚姻登记机关撤回离婚登记申请。"
                }
            },
            "劳动合同法": {
                "name": "中华人民共和国劳动合同法",
                "url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgwODE3MjY4YmI2MzAxNzI4YzQ5YzA0ODQwNmM",
                "articles": {
                    "试用期": "第19条：劳动合同期限三个月以上不满一年的，试用期不得超过一个月；劳动合同期限一年以上不满三年的，试用期不得超过二个月；三年以上固定期限和无固定期限的劳动合同，试用期不得超过六个月。",
                    "经济补偿": "第47条：经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资。六个月以上不满一年的，按一年计算；不满六个月的，向劳动者支付半个月工资的经济补偿。"
                }
            },
            "消费者权益保护法": {
                "name": "中华人民共和国消费者权益保护法",
                "url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgwODE3MjY4YmI2MzAxNzI4YzUyYzA0ODQwYjk",
                "articles": {
                    "退一赔三": "第55条：经营者提供商品或者服务有欺诈行为的，应当按照消费者的要求增加赔偿其受到的损失，增加赔偿的金额为消费者购买商品的价款或者接受服务的费用的三倍；增加赔偿的金额不足五百元的，为五百元。"
                }
            },
            "道路交通安全法": {
                "name": "中华人民共和国道路交通安全法",
                "url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgwODE3MjY4YmI2MzAxNzI4YzVhMTA0ODQwYjM",
                "articles": {}
            },
            "刑法": {
                "name": "中华人民共和国刑法",
                "url": "https://flk.npc.gov.cn/detail2.html?ZmY4MDgwODE3MjY4YmI2MzAxNzI4YzY1NjA0ODQwYjc",
                "articles": {}
            }
        }
    
    def search_law(self, query: str) -> List[Dict]:
        """根据关键词搜索相关法律条文"""
        results = []
        query_lower = query.lower()
        
        for law_key, law_info in self.laws.items():
            if law_key in query or law_key.lower() in query_lower:
                results.append({
                    "law_name": law_info["name"],
                    "url": law_info["url"],
                    "type": "法律"
                })
            
            for article_key, article_content in law_info["articles"].items():
                if article_key in query or article_key.lower() in query_lower:
                    results.append({
                        "law_name": law_info["name"],
                        "article": article_key,
                        "content": article_content,
                        "url": law_info["url"],
                        "type": "条文"
                    })
        
        return results
    
    def get_law_url(self, law_name: str) -> str:
        """获取法律原文链接"""
        for law_info in self.laws.values():
            if law_info["name"] == law_name:
                return law_info["url"]
        return "https://flk.npc.gov.cn/"

# ===================== 腾讯混元客户端 =====================
class HunyuanClient:
    def __init__(self, secret_id: str, secret_key: str, law_db: LocalLawDatabase):
        """初始化腾讯混元客户端"""
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.law_db = law_db
        
        cred = credential.Credential(secret_id, secret_key)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        
        self.client = hunyuan_client.HunyuanClient(cred, "ap-guangzhou", clientProfile)
    
    def search_laws(self, query: str) -> str:
        """搜索相关法律条文"""
        results = self.law_db.search_law(query)
        if results:
            context = "\n\n".join([
                f"【{r.get('law_name', '未知法律')}】\n{r.get('content', f'查看原文：{r.get(\"url\", \"\")}')}"
                for r in results
            ])
            return f"\n\n📚 **相关法律条文**（来自国家法律法规数据库）：\n{context}\n\n🔗 详细查询请访问：https://flk.npc.gov.cn/"
        return ""
    
    def chat(self, user_input: str, system_prompt: str = "") -> str:
        """单轮对话"""
        try:
            law_context = self.search_laws(user_input)
            
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            
            messages = []
            if system_prompt:
                messages.append({"Role": "system", "Content": system_prompt})
            
            full_prompt = user_input + law_context
            messages.append({"Role": "user", "Content": full_prompt})
            
            req.Messages = messages
            req.Temperature = 0.7
            
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            return f"❌ 请求失败：{str(e)}\n\n您也可以直接访问国家法律法规数据库 https://flk.npc.gov.cn/ 查询相关法律条文"
    
    def chat_with_history(self, history_messages: List[Dict], system_prompt: str = "") -> str:
        """支持多轮对话的法律咨询"""
        try:
            # 构建消息列表
            full_messages = []
            
            # 添加系统提示词
            if system_prompt:
                full_messages.append({"Role": "system", "Content": system_prompt})
            
            # 获取最新的用户消息用于检索法律条文
            latest_user_msg = ""
            for msg in reversed(history_messages):
                if msg.get("role") == "user":
                    latest_user_msg = msg.get("content", "")
                    break
            
            # 添加对话历史
            for msg in history_messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                if role == "user" and content:
                    full_messages.append({"Role": "user", "Content": content})
                elif role == "assistant" and content:
                    full_messages.append({"Role": "assistant", "Content": content})
            
            # 确保最后一条消息是user
            if not full_messages:
                # 如果没有历史消息，添加一个默认的用户消息
                full_messages.append({"Role": "user", "Content": latest_user_msg or "请继续"})
            elif full_messages[-1]["Role"] != "user":
                # 如果最后不是 user，添加一个默认的 user 消息
                full_messages.append({"Role": "user", "Content": latest_user_msg or "请继续"})
            
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            req.Messages = full_messages
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
            
        except Exception as e:
            error_msg = str(e)
            # 如果还是出错，降级到简单对话
            if "InvalidParameter" in error_msg:
                try:
                    # 降级方案：只发送当前问题
                    return self.chat(latest_user_msg if 'latest_user_msg' in locals() else "", system_prompt)
                except:
                    pass
            return f"❌ 请求失败：{error_msg}\n\n您也可以直接访问国家法律法规数据库 https://flk.npc.gov.cn/ 查询"

    def generate_document(self, doc_type: str, case_info: Dict) -> str:
        """生成法律文书"""
        try:
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            
            doc_prompts = {
                "起诉状": f"""请根据以下信息生成一份标准的民事起诉状：

原告信息：{case_info.get('plaintiff', '未提供')}
被告信息：{case_info.get('defendant', '未提供')}
诉讼请求：{case_info.get('claims', '未提供')}
事实与理由：{case_info.get('facts', '未提供')}

请按照法律文书格式生成，包括：标题、当事人信息、诉讼请求、事实与理由、此致、落款等。""",

                "答辩状": f"""请根据以下信息生成一份标准的民事答辩状：

被告信息：{case_info.get('defendant', '未提供')}
原告信息：{case_info.get('plaintiff', '未提供')}
答辩意见：{case_info.get('defense', '未提供')}

请按照法律文书格式生成。""",

                "上诉状": f"""请根据以下信息生成一份标准的民事上诉状：

上诉人：{case_info.get('appellant', '未提供')}
被上诉人：{case_info.get('appellee', '未提供')}
上诉请求：{case_info.get('requests', '未提供')}
上诉理由：{case_info.get('reasons', '未提供')}

请按照法律文书格式生成。""",

                "劳动仲裁申请书": f"""请根据以下信息生成一份劳动仲裁申请书：

申请人：{case_info.get('applicant', '未提供')}
被申请人：{case_info.get('respondent', '未提供')}
仲裁请求：{case_info.get('claims', '未提供')}
事实与理由：{case_info.get('facts', '未提供')}

请按照劳动仲裁申请书格式生成。"""
            }
            
            prompt = doc_prompts.get(doc_type, doc_prompts["起诉状"])
            
            req.Messages = [
                {"Role": "system", "Content": "你是专业的法律文书生成助手，请严格按照法律文书格式生成规范、严谨的法律文书。"},
                {"Role": "user", "Content": prompt}
            ]
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            return f"❌ 文书生成失败：{str(e)}"

    def process_node_reminder(self, case_type: str, case_details: str) -> str:
        """处理节点提醒功能"""
        try:
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            
            prompt = f"""请根据以下案件信息，分析并输出完整的法律流程节点和具体时间提醒：

案件类型：{case_type}
案件详情：{case_details}

请按以下格式输出：
1. 案件流程节点（按时间顺序列出每个关键节点）
2. 每个节点的具体法律时效和时间限制
3. 重要提醒事项（如证据保存、诉讼时效等）
4. 建议的行动步骤

请确保信息准确、实用。"""
            
            req.Messages = [
                {"Role": "system", "Content": "你是专业的法律流程助手，请结合国家法律法规，分析案件的关键节点、法律时效、流程提醒。回答要清晰易懂，标注重要时间节点。"},
                {"Role": "user", "Content": prompt}
            ]
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            return f"❌ 节点提醒服务请求失败：{str(e)}\n\n您也可以直接访问国家法律法规数据库 https://flk.npc.gov.cn/ 查询相关法律流程。"

# ===================== 页面配置 =====================
st.set_page_config(
    page_title="司法流程辅助系统", 
    page_icon="⚖️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .stChatMessage {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
    }
    .stButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 500;
    }
    .official-badge {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.title("⚖️ 司法流程辅助与节点提醒系统")
st.markdown("*连接国家法律法规数据库 | 智能法律咨询 | 多轮对话 | 文书生成 | 节点提醒*")

# ===================== 会话状态初始化 =====================
def init_session_state():
    """初始化所有 session state 变量"""
    if "hy_client" not in st.session_state:
        st.session_state.hy_client = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "mode" not in st.session_state:
        st.session_state.mode = "法律解释"
    if "law_db" not in st.session_state:
        st.session_state.law_db = LocalLawDatabase()
    if "first_message_sent" not in st.session_state:
        st.session_state.first_message_sent = False

init_session_state()

# ===================== 侧边栏 =====================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/law.png", width=80)
    st.markdown("## 📚 系统功能")
    
    st.markdown("---")
    
    # 国家法律法规数据库链接
    st.markdown("### 🏛️ 官方法律数据库")
    st.markdown("""
    <div style="background-color: #e8f5e9; padding: 10px; border-radius: 8px; margin: 10px 0;">
        <a href="https://flk.npc.gov.cn/" target="_blank" style="color: #2e7d32; text-decoration: none; font-weight: bold;">
            📖 国家法律法规数据库
        </a>
        <p style="font-size: 12px; color: #666; margin-top: 5px;">
            全国人大官网 · 权威法律检索
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 登录/退出
    if st.session_state.hy_client is not None:
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.hy_client = None
            st.session_state.messages = []
            st.rerun()
    
    st.markdown("---")
    
    # 模式选择
    st.markdown("### 🎯 对话模式")
    mode_options = {
        "法律解释": "📚 法律解释",
        "节点提醒": "⏰ 节点提醒", 
        "智能对话": "💬 智能对话",
        "文书生成": "📄 文书生成"
    }
    
    cols = st.columns(2)
    for i, (mode_key, mode_label) in enumerate(mode_options.items()):
        col = cols[i % 2]
        with col:
            if st.button(mode_label, key=f"mode_{mode_key}"):
                st.session_state.mode = mode_key
                st.rerun()
    
    st.markdown(f"**当前模式：** `{st.session_state.mode}`")
    
    st.markdown("---")
    
    # 对话控制
    st.markdown("### 🛠️ 对话控制")
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # 使用帮助
    with st.expander("ℹ️ 使用帮助"):
        st.markdown("""
        **功能介绍：**
        - 📚 **法律解释**：解读法律条文，匹配相关法条
        - ⏰ **节点提醒**：输入您的案件情况，获取法律流程节点和具体时间提醒
        - 💬 **智能对话**：日常法律咨询，通俗解释
        - 📄 **文书生成**：生成标准法律文书（起诉状、答辩状等）
        
        **数据来源：**
        - 🏛️ **国家法律法规数据库**（全国人大官网）
        
        **使用技巧：**
        - 支持多轮对话
        - 自动检索法律条文
        - 按Enter键发送消息
        """)
    
    st.markdown("---")
    st.caption("司法流程辅助系统 v2.0")
    st.caption("数据来源：国家法律法规数据库")

# ===================== 登录区域 =====================
if st.session_state.hy_client is None:
    st.markdown("## 🔐 系统登录")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("### 腾讯云密钥验证")
            st.caption("登录后可享受AI智能法律咨询 + 国家法律法规数据库检索 + 法律文书生成 + 节点提醒")
            
            secret_id = st.text_input("SecretId", placeholder="请输入腾讯云 SecretId", type="password")
            secret_key = st.text_input("SecretKey", placeholder="请输入腾讯云 SecretKey", type="password")
            
            submitted = st.form_submit_button("🔑 登录系统", use_container_width=True)
            
            if submitted:
                if not secret_id or not secret_key:
                    st.error("❌ 密钥不能为空！")
                else:
                    with st.spinner("正在验证密钥并初始化系统..."):
                        try:
                            cli = HunyuanClient(secret_id, secret_key, st.session_state.law_db)
                            test_result = cli.chat("测试连接", "你只需回复'正常'")
                            st.session_state.hy_client = cli
                            st.success("✅ 登录成功！已连接国家法律法规数据库")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 登录失败：{str(e)}")
    
    st.stop()

# ===================== 节点提醒模式 =====================
if st.session_state.mode == "节点提醒":
    st.markdown("## ⏰ 法律流程节点提醒")
    st.markdown("请填写您的案件情况，系统将为您分析法律流程节点和具体时间提醒")
    
    with st.form("node_reminder_form"):
        case_type = st.selectbox(
            "案件类型", 
            ["离婚纠纷", "合同纠纷", "劳动纠纷", "侵权纠纷", "继承纠纷", "房产纠纷", "消费者权益纠纷", "其他"]
        )
        
        case_details = st.text_area(
            "案件详情", 
            placeholder="请详细描述您的情况，例如：\n- 事件发生时间\n- 涉及的主要问题\n- 当前进展状态\n- 您的具体需求等",
            height=200
        )
        
        submitted = st.form_submit_button("🔍 分析流程节点", use_container_width=True)
        
        if submitted:
            if not case_details:
                st.error("❌ 请填写案件详情")
            else:
                with st.spinner("正在分析法律流程节点..."):
                    try:
                        result = st.session_state.hy_client.process_node_reminder(case_type, case_details)
                        st.markdown("### 📋 法律流程节点分析")
                        st.markdown(result)
                    except Exception as e:
                        st.error(f"❌ 分析失败：{str(e)}")
    
    st.stop()

# ===================== 文书生成模式 =====================
if st.session_state.mode == "文书生成":
    st.markdown("## 📄 法律文书生成")
    st.markdown("请填写以下信息，系统将自动生成标准法律文书")
    
    doc_type = st.selectbox("文书类型", ["起诉状", "答辩状", "上诉状", "劳动仲裁申请书"])
    
    with st.form("document_form"):
        if doc_type == "起诉状":
            plaintiff = st.text_area("原告信息", placeholder="姓名、性别、身份证号、住址、联系方式等")
            defendant = st.text_area("被告信息", placeholder="姓名、性别、身份证号、住址、联系方式等")
            claims = st.text_area("诉讼请求", placeholder="请列出具体的诉讼请求，每项一行")
            facts = st.text_area("事实与理由", placeholder="请详细描述案件事实和法律依据")
            
            submitted = st.form_submit_button("生成起诉状", use_container_width=True)
            
            if submitted:
                with st.spinner("正在生成起诉状..."):
                    case_info = {
                        "plaintiff": plaintiff,
                        "defendant": defendant,
                        "claims": claims,
                        "facts": facts
                    }
                    result = st.session_state.hy_client.generate_document("起诉状", case_info)
                    st.markdown("### 📝 生成的起诉状")
                    st.markdown(result)
        
        elif doc_type == "答辩状":
            defendant = st.text_area("被告信息", placeholder="姓名、性别、身份证号、住址、联系方式等")
            plaintiff = st.text_area("原告信息", placeholder="原告姓名")
            defense = st.text_area("答辩意见", placeholder="请列出答辩意见和法律依据")
            
            submitted = st.form_submit_button("生成答辩状", use_container_width=True)
            
            if submitted:
                with st.spinner("正在生成答辩状..."):
                    case_info = {
                        "defendant": defendant,
                        "plaintiff": plaintiff,
                        "defense": defense
                    }
                    result = st.session_state.hy_client.generate_document("答辩状", case_info)
                    st.markdown("### 📝 生成的答辩状")
                    st.markdown(result)
        
        elif doc_type == "上诉状":
            appellant = st.text_area("上诉人信息", placeholder="姓名、性别、身份证号等")
            appellee = st.text_area("被上诉人信息", placeholder="姓名、性别、身份证号等")
            requests = st.text_area("上诉请求", placeholder="请列出上诉请求")
            reasons = st.text_area("上诉理由", placeholder="请详细说明上诉理由")
            
            submitted = st.form_submit_button("生成上诉状", use_container_width=True)
            
            if submitted:
                with st.spinner("正在生成上诉状..."):
                    case_info = {
                        "appellant": appellant,
                        "appellee": appellee,
                        "requests": requests,
                        "reasons": reasons
                    }
                    result = st.session_state.hy_client.generate_document("上诉状", case_info)
                    st.markdown("### 📝 生成的上诉状")
                    st.markdown(result)
        
        elif doc_type == "劳动仲裁申请书":
            applicant = st.text_area("申请人信息", placeholder="姓名、性别、身份证号、住址、联系方式等")
            respondent = st.text_area("被申请人信息", placeholder="公司名称、法定代表人、地址等")
            claims = st.text_area("仲裁请求", placeholder="请列出具体的仲裁请求")
            facts = st.text_area("事实与理由", placeholder="请详细描述事实经过")
            
            submitted = st.form_submit_button("生成仲裁申请书", use_container_width=True)
            
            if submitted:
                with st.spinner("正在生成劳动仲裁申请书..."):
                    case_info = {
                        "applicant": applicant,
                        "respondent": respondent,
                        "claims": claims,
                        "facts": facts
                    }
                    result = st.session_state.hy_client.generate_document("劳动仲裁申请书", case_info)
                    st.markdown("### 📝 生成的劳动仲裁申请书")
                    st.markdown(result)
    
    st.stop()

# ===================== 主聊天区域 =====================
# 修复：只在没有消息时显示欢迎消息，但不清空用户输入
if not st.session_state.messages:
    welcome_msg = "您好！我是司法流程辅助系统，可以为您提供法律咨询、节点提醒和文书生成服务。请问有什么可以帮助您的？"
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

# 显示对话历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入框
prompt = st.chat_input("请输入您的法律问题，系统将自动检索国家法律法规数据库...")
if prompt:
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 系统提示词
    system_prompts = {
        "法律解释": "你是专业法律科普助手，请结合国家法律法规数据库的官方条文，通俗易懂地解读法律内容。回答中请注明法律条文来源，必要时提供官方链接。",
        "节点提醒": "你是专业流程助手，请结合国家法律法规，分析案件的关键节点、法律时效、流程提醒。回答要清晰易懂，标注重要时间节点。",
        "智能对话": "你是专业的法律顾问，请结合国家法律法规，用通俗易懂的语言解答法律问题。优先引用官方法律条文。",
        "文书生成": "你是专业法律文书助手，请依据国家法律法规，生成格式规范、内容严谨的标准法律文书。"
    }
    
    system_prompt = system_prompts.get(st.session_state.mode, system_prompts["智能对话"])
    
    # 获取AI回复 - 修复：传入完整的历史消息（包括刚添加的用户消息）
    with st.chat_message("assistant"):
        with st.spinner("🔍 正在检索国家法律法规数据库..."):
            try:
                # 修复：传入所有历史消息，而不是排除最后一条
                response = st.session_state.hy_client.chat_with_history(st.session_state.messages, system_prompt)
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
            except Exception as e:
                error_msg = f"❌ 请求失败：{str(e)}\n\n您也可以直接访问国家法律法规数据库 https://flk.npc.gov.cn/ 查询相关法律条文。"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# ===================== 页脚 =====================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 20px;'>"
    "⚖️ 司法流程辅助系统 | 数据来源：国家法律法规数据库 https://flk.npc.gov.cn/ | 提供权威法律咨询"
    "</div>",
    unsafe_allow_html=True
)
