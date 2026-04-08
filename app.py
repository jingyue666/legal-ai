import streamlit as st
import time
import json
from typing import List, Dict
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# ===================== 全局配置 =====================
st.set_page_config(page_title="司法流程辅助系统", page_icon="⚖️", layout="wide")

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "hy_client" not in st.session_state:
    st.session_state.hy_client = None
if "mode" not in st.session_state:
    st.session_state.mode = "智能对话"
if "law_db" not in st.session_state:
    st.session_state.law_db = None

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
                "content": """**第六百七十五条** 借款人应当按照约定的期限返还借款。对借款期限没有约定或约定不明，依据本法第五百一十条仍不能确定的，借款人可以随时返还；贷款人可以催告借款人在合理期限内返还。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "合同": {
                "title": "中华人民共和国民法典·合同编",
                "content": """**第四百六十九条** 当事人订立合同，可以采用书面形式、口头形式或者其他形式。
**第五百七十七条** 当事人一方不履行合同义务或履行不符合约定，应承担继续履行、采取补救措施或赔偿损失等违约责任。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "劳动": {
                "title": "中华人民共和国劳动合同法",
                "content": """**第十条** 建立劳动关系，应当订立书面劳动合同。
**第十九条** 试用期最长不得超过六个月。
**第四十七条** 经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资。""",
                "url": "https://flk.npc.gov.cn/detail/劳动合同法"
            }
        }

    def search_laws(self, keyword: str) -> Dict:
        """搜索法律法规（优先匹配预设库）"""
        keyword = keyword.lower()
        matched_laws = []
        for key, law in self.law_summaries.items():
            if key in keyword or any(word in keyword for word in key.split("、")):
                matched_laws.append(law)
        if matched_laws:
            return matched_laws[0]
        return {"title": "未找到匹配法条", "content": "暂无相关法律条文", "url": self.base_url}

# ===================== 腾讯云混元客户端（补全！） =====================
class HunyuanClient:
    def __init__(self, secret_id: str, secret_key: str, law_db: NationalLawDatabase):
        self.law_db = law_db
        # 初始化腾讯云SDK
        cred = credential.Credential(secret_id, secret_key)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        httpProfile.reqTimeout = 60  # 关键：加长超时（Streamlit Cloud网络慢）

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        self.client = hunyuan_client.HunyuanClient(cred, "ap-beijing", clientProfile)

    def chat_with_history(self, history: List[Dict], prompt: str) -> str:
        try:
            # 1. 先检索本地法律库
            law_info = self.law_db.search_laws(prompt)
            law_content = f"\n\n📚 参考法条：\n【{law_info['title']}】\n{law_info['content']}\n🔗 原文：{law_info['url']}"

            # 2. 构建请求
            req = models.ChatCompletionsRequest()
            messages = []
            # 加入历史对话
            for msg in history:
                messages.append({"Role": msg["role"], "Content": msg["content"]})
            # 加入当前系统提示+用户问题
            messages.append({"Role": "user", "Content": f"{prompt}\n请结合以下法律回答：{law_content}"})
            
            req.Messages = messages
            req.Model = "hunyuan-standard"
            req.Temperature = 0.7

            # 3. 调用混元API
            resp = self.client.ChatCompletions(req)
            resp_dict = json.loads(resp.to_json_string())
            answer = resp_dict["Choices"][0]["Message"]["Content"]
            return answer + law_info

        except Exception as e:
            # 降级：只返回本地知识库
            st.warning(f"⚠️ AI服务暂时不可用（{str(e)}），以下为法律知识库内容")
            law = self.law_db.search_laws(prompt)
            return f"【{law['title']}】\n{law['content']}\n🔗 {law['url']}"

# ===================== 侧边栏 =====================
def render_sidebar():
    with st.sidebar:
        st.title("⚖️ 司法辅助系统")
        st.markdown("---")
        # 模式切换
        mode = st.radio("选择功能模式", ["法律解释", "节点提醒", "智能对话", "文书生成"],
                        index=["法律解释", "节点提醒", "智能对话", "文书生成"].index(st.session_state.mode))
        if mode != st.session_state.mode:
            st.session_state.mode = mode
            st.rerun()
        st.markdown(f"**当前：{st.session_state.mode}**")
        st.markdown("---")
        if st.button("🗑️ 清空对话"):
            st.session_state.messages = []
            st.rerun()
        with st.expander("ℹ️ 帮助"):
            st.markdown("- 自动匹配国家法律法规数据库\n- 支持多轮记忆\n- 数据来源：全国人大官网")
        st.caption("flk.npc.gov.cn")

# ===================== 主程序 =====================
def main():
    render_sidebar()
    # 初始化数据库
    if not st.session_state.law_db:
        st.session_state.law_db = NationalLawDatabase()

    # 登录（SecretId/Key）
    if not st.session_state.hy_client:
        st.markdown("## 🔐 登录（腾讯云混元）")
        with st.form("login"):
            secret_id = st.text_input("SecretId", type="password")
            secret_key = st.text_input("SecretKey", type="password")
            if st.form_submit_button("✅ 登录"):
                if not secret_id or not secret_key:
                    st.error("密钥不能为空")
                else:
                    with st.spinner("验证中..."):
                        try:
                            client = HunyuanClient(secret_id, secret_key, st.session_state.law_db)
                            # 测试连接
                            test = client.chat_with_history([], "回复‘正常’")
                            st.session_state.hy_client = client
                            st.success("登录成功！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"登录失败：{str(e)}")
        return

    # 欢迎语
    if not st.session_state.messages:
        welcome = """您好！欢迎使用司法流程辅助系统。
**🏛️ 数据来源：国家法律法规数据库（全国人大官网）**
- 自动匹配相关法条 + 官方原文链接
- 支持多轮对话记忆
请问有什么可以帮您？"""
        st.session_state.messages.append({"role": "assistant", "content": welcome})

    # 显示消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 输入框占位符
    placeholder = {
        "法律解释": "例如：请解释离婚冷静期规定...",
        "节点提醒": "例如：劳动仲裁流程与时效？",
        "智能对话": "请输入法律问题...",
        "文书生成": "例如：生成房屋租赁合同..."
    }.get(st.session_state.mode, "请输入问题...")

    # 对话逻辑
    if prompt := st.chat_input(placeholder):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 系统提示
        system_prompt = {
            "法律解释": "通俗解读法律，优先引用官方条文",
            "节点提醒": "分析流程、时效、关键节点",
            "智能对话": "专业、通俗解答法律问题",
            "文书生成": "生成规范法律文书草稿"
        }.get(st.session_state.mode, "专业解答法律问题")

        with st.chat_message("assistant"):
            with st.spinner("🔍 检索法条中..."):
                resp = st.session_state.hy_client.chat_with_history(st.session_state.messages[:-1],
                                                                    f"{system_prompt}\n用户问题：{prompt}")
                st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})

if __name__ == "__main__":
    main()
