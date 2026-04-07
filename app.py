import streamlit as st
import time
import json
import os
import requests
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
人民法院审理离婚案件，应当进行调解；如果感情确已破裂，调解无效的，应当准予离婚。
有下列情形之一，调解无效的，应当准予离婚：
(一)重婚或者与他人同居；
(二)实施家庭暴力或者虐待、遗弃家庭成员；
(三)有赌博、吸毒等恶习屡教不改；
(四)因感情不和分居满二年；
(五)其他导致夫妻感情破裂的情形。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "欠钱": {
                "title": "中华人民共和国民法典·合同编",
                "content": """**第六百七十五条** 借款人应当按照约定的期限返还借款。对借款期限没有约定或者约定不明确，依据本法第五百一十条的规定仍不能确定的，借款人可以随时返还；贷款人可以催告借款人在合理期限内返还。

**第六百七十六条** 借款人未按照约定的期限返还借款的，应当按照约定或者国家有关规定支付逾期利息。

**第六百七十九条** 自然人之间的借款合同，自贷款人提供借款时成立。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "合同": {
                "title": "中华人民共和国民法典·合同编",
                "content": """**第四百六十九条** 当事人订立合同，可以采用书面形式、口头形式或者其他形式。

**第五百七十七条** 当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。""",
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
                "content": """**第一千一百六十五条** 行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。
**第一千一百七十九条** 侵害他人造成人身损害的，应当赔偿医疗费、护理费、交通费等合理费用。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "继承": {
                "title": "中华人民共和国民法典·继承编",
                "content": """**第一千一百二十七条** 遗产按照下列顺序继承：第一顺序：配偶、子女、父母；第二顺序：兄弟姐妹、祖父母、外祖父母。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            }
        }

    def search_laws(self, keyword: str) -> Dict:
        """搜索法律法规（优先预设库）"""
        matched = []
        kw_lower = keyword.lower()
        for key, law in self.law_summaries.items():
            if key in kw_lower or kw_lower in key:
                matched.append({
                    "title": law["title"],
                    "content": law["content"],
                    "url": law.get("url", self.base_url),
                    "source": "预设法律知识库"
                })
        if matched:
            return {"success": True, "total": len(matched), "list": matched, "source": "预设库"}
        
        # 尝试访问官网API（可选，因跨域限制通常失败）
        try:
            params = {"keyword": keyword, "page": 1, "pageSize": 3}
            resp = requests.get("https://flk.npc.gov.cn/api/search", params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                items = []
                for item in data.get("list", [])[:3]:
                    items.append({
                        "title": item.get("title", ""),
                        "content": item.get("summary", ""),
                        "url": f"https://flk.npc.gov.cn/detail/{item.get('id', '')}",
                        "source": "国家法律法规数据库"
                    })
                return {"success": True, "total": len(items), "list": items, "source": "官网API"}
        except Exception:
            pass
        
        return {"success": False, "total": 0, "list": [], "message": "未找到相关法律条文，请访问官网查询"}

# ===================== 本地法律知识库 =====================
class LocalLawDatabase:
    def __init__(self, law_file="law_database.json"):
        self.law_file = law_file
        self.laws = {}
        self.load_laws()
    def load_laws(self):
        if os.path.exists(self.law_file):
            try:
                with open(self.law_file, 'r', encoding='utf-8') as f:
                    self.laws = json.load(f)
            except:
                self.create_default()
        else:
            self.create_default()
            self.save()
    def create_default(self):
        self.laws = {
            "婚姻法": {"keywords": ["离婚","结婚","婚姻"], "content": "参考《中华人民共和国民法典》婚姻家庭编"},
            "合同法": {"keywords": ["合同","违约"], "content": "参考《中华人民共和国民法典》合同编"},
            "劳动法": {"keywords": ["劳动","工资"], "content": "参考《中华人民共和国劳动合同法》"}
        }
    def save(self):
        try:
            with open(self.law_file, 'w', encoding='utf-8') as f:
                json.dump(self.laws, f, ensure_ascii=False, indent=2)
        except:
            pass
    def search_law(self, query):
        results = []
        for name, data in self.laws.items():
            if any(k in query for k in data.get("keywords", [])):
                results.append({"law_name": name, "content": data.get("content",""), "relevance": 1})
        return results[:3]

# ===================== 腾讯混元客户端 =====================
class HunyuanClient:
    def __init__(self, secret_id, secret_key, law_db):
        cred = credential.Credential(secret_id, secret_key)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        self.client = hunyuan_client.HunyuanClient(cred, "ap-beijing", clientProfile)
        self.law_db = law_db
        self.national_db = NationalLawDatabase()

    def chat_with_history(self, messages, system_prompt):
        """支持多轮对话，自动修复消息格式（确保以 assistant 结尾）"""
        try:
            # 提取最新用户消息用于检索
            latest_user = ""
            for m in reversed(messages):
                if m["role"] == "user":
                    latest_user = m["content"]
                    break
            # 检索法律知识
            law_results = self.national_db.search_laws(latest_user)
            enhanced_system = system_prompt
            if law_results.get("success") and law_results.get("list"):
                context = "\n\n**【国家法律法规数据库检索结果】**\n"
                for law in law_results["list"][:2]:
                    context += f"\n### {law['title']}\n{law['content'][:500]}\n"
                    if law.get('url'):
                        context += f"🔗 原文链接：{law['url']}\n"
                enhanced_system += context

            # 构建消息列表
            full_messages = [{"Role": "system", "Content": enhanced_system}]
            for msg in messages:
                role = "assistant" if msg["role"] == "assistant" else "user"
                full_messages.append({"Role": role, "Content": msg["content"]})
            
            # 关键修复：确保最后一条消息是 assistant
            if full_messages and full_messages[-1]["Role"] in ("user", "tool"):
                full_messages.append({"Role": "assistant", "Content": "请继续。"})

            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            req.Messages = full_messages
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            # 降级：返回预设法律知识
            fallback = f"请求失败：{str(e)}\n\n您也可以直接访问国家法律法规数据库 https://flk.npc.gov.cn/ 查询。"
            if 'law_results' in locals() and law_results.get("list"):
                fallback = "【AI服务暂时不可用，以下为法律知识库内容】\n\n"
                for law in law_results["list"][:2]:
                    fallback += f"### {law['title']}\n{law['content']}\n🔗 {law.get('url', '')}\n\n"
            return fallback

# ===================== Streamlit UI =====================
st.set_page_config(page_title="司法流程辅助系统", page_icon="⚖️", layout="wide")
st.title("⚖️ 司法流程辅助与节点提醒系统")
st.markdown("*连接国家法律法规数据库 | 智能法律咨询 | 多轮对话*")

# 初始化session
if "hy_client" not in st.session_state:
    st.session_state.hy_client = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = "智能对话"
if "law_db" not in st.session_state:
    st.session_state.law_db = LocalLawDatabase()

# 侧边栏
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/law.png", width=80)
    st.markdown("## 🏛️ 官方法律数据库")
    st.markdown("[📖 国家法律法规数据库](https://flk.npc.gov.cn/)  \n*全国人大官网·权威法律检索*")
    st.markdown("---")
    if st.session_state.hy_client is not None:
        if st.button("🚪 退出登录"):
            st.session_state.hy_client = None
            st.session_state.messages = []
            st.rerun()
    st.markdown("### 🎯 对话模式")
    modes = {"法律解释": "📚", "节点提醒": "⏰", "智能对话": "💬", "文书生成": "📄"}
    cols = st.columns(2)
    for i, (mode, icon) in enumerate(modes.items()):
        with cols[i%2]:
            if st.button(f"{icon} {mode}", key=mode):
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
        - 系统会自动检索国家法律法规数据库（预设库）
        """)
    st.caption("数据来源：国家法律法规数据库 https://flk.npc.gov.cn/")

# 登录区域
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
                        # 测试连接
                        test_resp = client.chat_with_history([], "你只需回复'正常'")
                        st.session_state.hy_client = client
                        st.success("登录成功！")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"登录失败：{str(e)}")
    st.stop()

# 显示欢迎消息
if not st.session_state.messages:
    welcome = """您好！欢迎使用司法流程辅助系统。

**🏛️ 数据来源：国家法律法规数据库（全国人大官网）**
- 官网地址：https://flk.npc.gov.cn/

**💡 使用提示：**
- 提问时会自动匹配相关法律条文
- 回答中将提供官方原文链接（如有）
- 支持多轮对话记忆

请问有什么可以帮您的吗？"""
    st.session_state.messages.append({"role": "assistant", "content": welcome})

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===================== 动态输入框占位符 =====================
placeholder_map = {
    "法律解释": "例如：请解释一下民法典关于离婚冷静期的规定...",
    "节点提醒": "例如：劳动仲裁的流程和时间节点有哪些？",
    "智能对话": "请输入您的法律问题，系统将自动检索国家法律法规数据库...",
    "文书生成": "例如：帮我生成一份标准的房屋租赁合同..."
}
current_mode = st.session_state.mode
input_placeholder = placeholder_map.get(current_mode, "请输入您的法律问题...")

# 输入框
if prompt := st.chat_input(input_placeholder):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompts = {
        "法律解释": "你是专业法律科普助手，请通俗易懂地解读法律内容，优先引用官方法律条文。",
        "节点提醒": "你是专业流程助手，分析案件节点、时效，清晰列出重要提醒。",
        "智能对话": "你是专业法律顾问，用通俗语言解答法律问题。",
        "文书生成": "你是法律文书助手，生成格式规范的法律文书。"
    }
    system_prompt = system_prompts.get(st.session_state.mode, system_prompts["智能对话"])

    with st.chat_message("assistant"):
        with st.spinner("🔍 正在检索法律知识库..."):
            history = st.session_state.messages[:-1]  # 不包括刚添加的用户消息
            response = st.session_state.hy_client.chat_with_history(history, system_prompt)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
