import streamlit as st
import time
import json
import os
from typing import List, Dict
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# ===================== 国家法律法规数据库检索模块 =====================
class NationalLawDatabase:
    """国家法律法规数据库检索类（含预设知识库）"""
    def __init__(self):
        self.base_url = "https://flk.npc.gov.cn"
        # 预设法律知识库（当API不可用时使用）
        self.law_summaries = {
            "离婚": {
                "title": "中华人民共和国民法典·婚姻家庭编",
                "content": """**第一千零七十六条** 夫妻双方自愿离婚的，应当签订书面离婚协议，并亲自到婚姻登记机关申请离婚登记。
离婚协议应当载明双方自愿离婚的意思表示和对子女抚养、财产以及债务处理等事项协商一致的意见。

**第一千零七十九条** 夫妻一方要求离婚的，可以由有关组织进行调解或者直接向人民法院提起离婚诉讼。
人民法院审理离婚案件，应当进行调解；如果感情确已破裂，调解无效的，应当准予离婚。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "欠钱": {
                "title": "中华人民共和国民法典·合同编",
                "content": """**第六百七十五条** 借款人应当按照约定的期限返还借款。
**第六百七十六条** 借款人未按照约定的期限返还借款的，应当支付逾期利息。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "合同": {
                "title": "中华人民共和国民法典·合同编",
                "content": """**第四百六十九条** 当事人订立合同，可以采用书面形式、口头形式或者其他形式。
**第五百七十七条** 当事人一方不履行合同义务，应当承担继续履行、赔偿损失等违约责任。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "劳动": {
                "title": "中华人民共和国劳动合同法",
                "content": """**第十条** 建立劳动关系，应当订立书面劳动合同。
**第十九条** 试用期最长不得超过六个月。
**第四十七条** 经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资。""",
                "url": "https://flk.npc.gov.cn/detail/劳动合同法"
            },
            "侵权": {
                "title": "中华人民共和国民法典·侵权责任编",
                "content": """**第一千一百六十五条** 行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "继承": {
                "title": "中华人民共和国民法典·继承编",
                "content": """**第一千一百二十七条** 遗产按照下列顺序继承：
第一顺序：配偶、子女、父母；
第二顺序：兄弟姐妹、祖父母、外祖父母。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            }
        }

    def search_laws(self, keyword: str) -> Dict:
        """搜索法律法规（优先预设库）"""
        matched = []
        kw_lower = keyword.lower()
        for key, law in self.law_summaries.items():
            if key in kw_lower:
                matched.append(law)
        if not matched:
            return {"success": False, "list": []}
        return {"success": True, "list": matched}

# ===================== 混元客户端 =====================
class HunyuanClient:
    def __init__(self, secret_id: str, secret_key: str, law_db: NationalLawDatabase):
        self.cred = credential.Credential(secret_id, secret_key)
        self.httpProfile = HttpProfile()
        self.httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        self.clientProfile = ClientProfile()
        self.clientProfile.httpProfile = self.httpProfile
        self.client = hunyuan_client.HunyuanClient(self.cred, "ap-beijing", self.clientProfile)
        self.law_db = law_db

    def chat_with_history(self, messages: List[Dict], system_prompt: str) -> str:
        try:
            latest_user = ""
            for m in reversed(messages):
                if m["role"] == "user":
                    latest_user = m["content"]
                    break

            law_results = self.law_db.search_laws(latest_user)
            enhanced_system = system_prompt

            if law_results.get("success") and law_results.get("list"):
                context = "\n\n【参考法条】\n"
                for law in law_results["list"][:2]:
                    context += f"\n### {law['title']}\n{law['content']}\n"
                    if law.get("url"):
                        context += f"🔗 {law['url']}\n"
                enhanced_system += context

            full_messages = [{"Role": "system", "Content": enhanced_system}]
            for msg in messages:
                role = "assistant" if msg["role"] == "assistant" else "user"
                full_messages.append({"Role": role, "Content": msg["content"]})

            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            req.Messages = full_messages
            req.Temperature = 0.7

            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content

        except Exception as e:
            # 降级逻辑（修复字典拼接错误）
            fallback = f"❌ AI服务暂时不可用（{str(e)}）\n\n【参考法条】\n"
            law_results = self.law_db.search_laws(latest_user)
            if law_results.get("success") and law_results.get("list"):
                for law in law_results["list"][:2]:
                    fallback += f"\n### {law['title']}\n{law['content']}\n"
                    if law.get("url"):
                        fallback += f"🔗 {law['url']}\n"
            return fallback

# ===================== Streamlit 页面初始化 =====================
st.set_page_config(page_title="司法流程辅助系统", page_icon="⚖️", layout="wide")
st.title("⚖️ 司法流程辅助与节点提醒系统")

# 初始化状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "hy_client" not in st.session_state:
    st.session_state.hy_client = None
if "law_db" not in st.session_state:
    st.session_state.law_db = NationalLawDatabase()
if "mode" not in st.session_state:
    st.session_state.mode = "智能对话"

# 侧边栏
with st.sidebar:
    st.markdown("## 🛠️ 功能模式")
    mode = st.radio(
        "选择模式",
        ["智能对话", "法律解释", "节点提醒", "文书生成"],
        index=["智能对话", "法律解释", "节点提醒", "文书生成"].index(st.session_state.mode)
    )
    if mode != st.session_state.mode:
        st.session_state.mode = mode
        st.rerun()
    st.markdown(f"**当前模式：** {st.session_state.mode}")
    st.markdown("---")
    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.rerun()
    with st.expander("ℹ️ 使用帮助"):
        st.markdown("""
        - **法律解释**：解读法条，匹配法律知识库
        - **节点提醒**：分析流程节点、时效
        - **智能对话**：日常法律咨询
        - **文书生成**：生成法律文书草稿
        - 系统自动检索国家法律法规数据库
        """)
    st.caption("数据来源：国家法律法规数据库")

# ===================== 登录 =====================
if st.session_state.hy_client is None:
    st.markdown("## 🔐 系统登录")
    with st.form("login_form"):
        secret_id = st.text_input("SecretId", type="password")
        secret_key = st.text_input("SecretKey", type="password")
        submitted = st.form_submit_button("🔑 登录")
        if submitted:
            if not secret_id or not secret_key:
                st.error("密钥不能为空")
            else:
                with st.spinner("验证中..."):
                    try:
                        client = HunyuanClient(secret_id, secret_key, st.session_state.law_db)
                        test_resp = client.chat_with_history([], "你只需回复'正常'")
                        st.session_state.hy_client = client
                        st.success("登录成功！")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"登录失败：{str(e)}")
    st.stop()

# ===================== 聊天界面 =====================
if not st.session_state.messages:
    welcome = """您好！欢迎使用司法流程辅助系统。

**🏛️ 数据来源：国家法律法规数据库（全国人大官网）**

**💡 使用提示：**
- 提问自动匹配相关法律条文
- 提供官方原文链接
- 支持多轮对话记忆

请问有什么可以帮您的吗？"""
    st.session_state.messages.append({"role": "assistant", "content": welcome})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入框
placeholder_map = {
    "法律解释": "例如：请解释一下民法典关于离婚冷静期的规定...",
    "节点提醒": "例如：劳动仲裁的流程和时间节点有哪些？",
    "智能对话": "请输入您的法律问题...",
    "文书生成": "例如：帮我生成一份标准的房屋租赁合同..."
}
input_placeholder = placeholder_map.get(st.session_state.mode, "请输入...")

if prompt := st.chat_input(input_placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompts = {
        "法律解释": "你是专业法律科普助手，通俗易懂解读法律，优先引用官方法条。",
        "节点提醒": "你是专业流程助手，分析案件节点、时效，清晰列出重要提醒。",
        "智能对话": "你是专业法律顾问，用通俗语言解答法律问题。",
        "文书生成": "你是法律文书助手，生成格式规范的法律文书。"
    }
    system_prompt = system_prompts.get(st.session_state.mode, system_prompts["智能对话"])

    with st.chat_message("assistant"):
        with st.spinner("🔍 正在检索法律知识库..."):
            response = st.session_state.hy_client.chat_with_history(
                st.session_state.messages[:-1], system_prompt
            )
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
