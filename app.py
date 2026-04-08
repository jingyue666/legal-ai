import streamlit as st
import time
import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 导入腾讯云SDK
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# 导入requests
import requests

# ===================== 国家法律法规数据库检索模块 =====================
class NationalLawDatabase:
    """国家法律法规数据库检索类"""
    
    def __init__(self):
        self.base_url = "https://flk.npc.gov.cn"
        self.search_url = "https://flk.npc.gov.cn/api/search"
        
        # 预设的法律知识库
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
            "结婚": {
                "title": "中华人民共和国民法典·婚姻家庭编",
                "content": """**第一千零四十六条** 结婚应当男女双方完全自愿，禁止任何一方对另一方加以强迫，禁止任何组织或者个人加以干涉。

**第一千零四十七条** 结婚年龄，男不得早于二十二周岁，女不得早于二十周岁。

**第一千零四十八条** 直系血亲或者三代以内的旁系血亲禁止结婚。

**第一千零四十九条** 要求结婚的男女双方应当亲自到婚姻登记机关申请结婚登记。符合本法规定的，予以登记，发给结婚证。完成结婚登记，即确立婚姻关系。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "合同": {
                "title": "中华人民共和国民法典·合同编",
                "content": """**第四百六十九条** 当事人订立合同，可以采用书面形式、口头形式或者其他形式。

**第五百七十七条** 当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。

**第五百七十八条** 当事人一方明确表示或者以自己的行为表明不履行合同义务的，对方可以在履行期限届满前请求其承担违约责任。

**第五百八十四条** 当事人一方不履行合同义务或者履行合同义务不符合约定，造成对方损失的，损失赔偿额应当相当于因违约所造成的损失，包括合同履行后可以获得的利益。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "劳动": {
                "title": "中华人民共和国劳动合同法",
                "content": """**第十条** 建立劳动关系，应当订立书面劳动合同。
已建立劳动关系，未同时订立书面劳动合同的，应当自用工之日起一个月内订立书面劳动合同。

**第十九条** 劳动合同期限三个月以上不满一年的，试用期不得超过一个月；劳动合同期限一年以上不满三年的，试用期不得超过二个月；三年以上固定期限和无固定期限的劳动合同，试用期不得超过六个月。

**第四十七条** 经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资。六个月以上不满一年的，按一年计算；不满六个月的，向劳动者支付半个月工资的经济补偿。

**第八十七条** 用人单位违反本法规定解除或者终止劳动合同的，应当依照本法第四十七条规定的经济补偿标准的二倍向劳动者支付赔偿金。""",
                "url": "https://flk.npc.gov.cn/detail/劳动合同法"
            },
            "侵权": {
                "title": "中华人民共和国民法典·侵权责任编",
                "content": """**第一千一百六十五条** 行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。
依照法律规定推定行为人有过错，其不能证明自己没有过错的，应当承担侵权责任。

**第一千一百七十九条** 侵害他人造成人身损害的，应当赔偿医疗费、护理费、交通费、营养费、住院伙食补助费等为治疗和康复支出的合理费用，以及因误工减少的收入。

**第一千一百八十三条** 侵害自然人人身权益造成严重精神损害的，被侵权人有权请求精神损害赔偿。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "继承": {
                "title": "中华人民共和国民法典·继承编",
                "content": """**第一千一百二十七条** 遗产按照下列顺序继承：
(一)第一顺序：配偶、子女、父母；
(二)第二顺序：兄弟姐妹、祖父母、外祖父母。
继承开始后，由第一顺序继承人继承，第二顺序继承人不继承；没有第一顺序继承人继承的，由第二顺序继承人继承。

**第一千一百三十条** 同一顺序继承人继承遗产的份额，一般应当均等。
对生活有特殊困难又缺乏劳动能力的继承人，分配遗产时，应当予以照顾。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            }
        }
    
    def search_laws(self, keyword: str, law_type: str = "all", page: int = 1, page_size: int = 10) -> Dict:
        """搜索法律法规"""
        matched_laws = self._search_from_preset(keyword)
        
        if matched_laws:  # 优先从预设知识库搜索
            return {
                "success": True,
                "total": len(matched_laws),
                "list": matched_laws,
                "keyword": keyword,
                "source": "法律知识库"
            }
        
        try:  # 从国家法律法规数据库搜索
            params = {
                "keyword": keyword,
                "page": page,
                "pageSize": page_size,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(self.search_url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("list"):
                    return {
                        "success": True,
                        "total": data.get("total", 0),
                        "list": self._parse_search_results(data.get("list", [])),
                        "keyword": keyword,
                        "source": "国家法律法规数据库"
                    }
        except Exception:
            pass
        
        return self._get_empty_result(keyword)
    
    def _search_from_preset(self, keyword: str) -> List:  # 从预设知识库搜索
        """从预设知识库搜索"""
        results = []
        keyword_lower = keyword.lower()
        
        for key, law in self.law_summaries.items():
            if key in keyword_lower or keyword_lower in key:
                results.append({
                    "id": key,
                    "title": law["title"],
                    "content": law["content"],
                    "law_type": "法律",
                    "pub_date": "",
                    "pub_org": "全国人民代表大会",
                    "validity": "有效",
                    "summary": law["content"][:200],
                    "url": law.get("url", "https://flk.npc.gov.cn/")
                })
        
        return results
    
    def _parse_search_results(self, results: List) -> List:  # 解析国家法律法规数据库搜索结果
        """解析搜索结果"""
        parsed = []
        for item in results:
            parsed.append({
                "id": item.get("id", ""),
                "title": item.get("title", ""),
                "law_type": item.get("type", ""),
                "pub_date": item.get("pubDate", ""),
                "pub_org": item.get("pubOrg", ""),
                "validity": item.get("validity", ""),
                "summary": item.get("summary", "")[:200] if item.get("summary") else "",
                "url": f"https://flk.npc.gov.cn/detail/{item.get('id', '')}"
            })
        return parsed
    
    def _get_empty_result(self, keyword: str, error_msg: str = "") -> Dict:  # 返回空结果
        """返回空结果"""
        return {
            "success": False,
            "total": 0,
            "list": [],
            "keyword": keyword,
            "message": f"请访问国家法律法规数据库查询：https://flk.npc.gov.cn/"
        }
    
    def get_recommended_link(self, keyword: str) -> str:  # 获取推荐查询链接
        """获取推荐查询链接"""
        return f"https://flk.npc.gov.cn/?keyword={keyword}"

# ===================== 本地法律知识库 =====================
class LocalLawDatabase:
    """本地法律知识库"""
    
    def __init__(self, law_file="law_database.json"):
        self.law_file = law_file
        self.laws = {}
        self.load_laws()
    
    def load_laws(self):
        """从JSON文件加载法律知识"""
        if os.path.exists(self.law_file):
            try:
                with open(self.law_file, 'r', encoding='utf-8') as f:
                    self.laws = json.load(f)
            except Exception:
                self.create_default_laws()
        else:
            self.create_default_laws()
            self.save_laws()
    
    def create_default_laws(self):
        """创建默认法律库"""
        self.laws = {
            "民法典": {
                "keywords": ["离婚", "结婚", "合同", "侵权", "继承", "物权"],
                "content": "《中华人民共和国民法典》是新中国第一部以法典命名的法律，共7编、1260条。"
            },
            "劳动合同法": {
                "keywords": ["劳动", "工资", "加班", "辞职", "辞退", "试用期"],
                "content": "《中华人民共和国劳动合同法》是为了完善劳动合同制度，保护劳动者合法权益的法律。"
            }
        }
    
    def save_laws(self):
        """保存法律库到JSON文件"""
        try:
            with open(self.law_file, 'w', encoding='utf-8') as f:
                json.dump(self.laws, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

# ===================== 用户信息收集与管理 =====================
class UserInfoManager:
    """用户信息管理器"""
    
    def __init__(self):
        self.user_info_fields = {
            "basic": {
                "name": "姓名",
                "age": "年龄",
                "occupation": "职业",
                "education": "学历"
            },
            "case_related": {
                "case_type": "案件类型",
                "case_role": "您在案件中的角色",
                "incident_date": "事件发生时间",
                "current_status": "当前进展状态"
            },
            "contact": {
                "phone": "联系电话",
                "email": "电子邮箱",
                "address": "通讯地址"
            }
        }
    
    def get_missing_fields(self, collected_info: Dict) -> List:
        """获取未填写的字段"""
        missing = []
        for category, fields in self.user_info_fields.items():
            for key, label in fields.items():
                if key not in collected_info or not collected_info[key]:
                    missing.append({"key": key, "label": label, "category": category})
        return missing
    
    def format_user_info(self, collected_info: Dict) -> str:
        """格式化用户信息用于系统提示"""
        if not collected_info:
            return "暂无用户信息"
        
        info_str = "\n**用户信息：**\n"
        
        # 基本信息
        basic_info = []
        for key, label in self.user_info_fields["basic"].items():
            if key in collected_info and collected_info[key]:
                basic_info.append(f"- {label}：{collected_info[key]}")
        if basic_info:
            info_str += "\n".join(basic_info) + "\n"
        
        # 案件信息
        case_info = []
        for key, label in self.user_info_fields["case_related"].items():
            if key in collected_info and collected_info[key]:
                case_info.append(f"- {label}：{collected_info[key]}")
        if case_info:
            info_str += "\n" + "\n".join(case_info) + "\n"
        
        return info_str

# ===================== 混元AI客户端 =====================
class HunyuanClient:
    def __init__(self, secret_id, secret_key, law_db, user_info_manager):  # 初始化混元AI客户端
        self.cred = credential.Credential(secret_id, secret_key)
        self.httpProfile = HttpProfile()
        self.httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        self.clientProfile = ClientProfile()
        self.clientProfile.httpProfile = self.httpProfile
        self.client = hunyuan_client.HunyuanClient(self.cred, "ap-beijing", self.clientProfile)
        self.law_db = law_db
        self.national_law_db = NationalLawDatabase()
        self.user_info_manager = user_info_manager  # 存储 user_info_manager

    def search_national_laws(self, keyword: str) -> Dict:  # 搜索国家法律法规数据库
        """搜索国家法律法规数据库"""
        return self.national_law_db.search_laws(keyword)

    def chat(self, prompt, system_prompt):
        """通用对话接口"""
        try:
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            
            # 搜索国家法律法规数据库
            national_laws = self.national_law_db.search_laws(prompt)
            
            enhanced_system_prompt = system_prompt
            
            # 添加国家法律法规数据库结果
            if national_laws.get("success") and national_laws.get("list"):
                law_context = "\n\n**【国家法律法规数据库检索结果】**\n"
                law_context += f"🔍 搜索关键词：{prompt}\n"
                law_context += f"📊 共找到 {national_laws.get('total', 0)} 条相关法规\n\n"
                
                for law in national_laws.get("list", [])[:3]:
                    law_context += f"### 📜 {law.get('title', '未知标题')}\n"
                    law_context += f"{law.get('content', law.get('summary', ''))}\n"
                    if law.get('url'):
                        law_context += f"\n🔗 查看原文：{law.get('url')}\n"
                    law_context += "\n"
                
                enhanced_system_prompt += law_context + "\n请优先引用以上官方法律条文，给出专业、准确的回答。"
            else:
                search_url = self.national_law_db.get_recommended_link(prompt)
                enhanced_system_prompt += f"\n\n如需查询更多相关法律条文，请访问国家法律法规数据库：{search_url}"
            
            # 构建消息 - 只包含 system 和 user
            messages = [
                {"Role": "system", "Content": enhanced_system_prompt},
                {"Role": "user", "Content": prompt}
            ]
            
            req.Messages = messages
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            return f"❌ AI服务请求失败：{str(e)}\n\n您也可以直接访问国家法律法规数据库 https://flk.npc.gov.cn/ 查询"

    def chat_with_history(self, messages, system_prompt, user_info: Dict = None):
        """支持多轮对话，并整合用户信息"""
        try:
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            
            # 获取最新的用户消息
            latest_user_msg = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    latest_user_msg = msg["content"]
                    break
            
            # 搜索国家法律法规数据库
            national_laws = self.national_law_db.search_laws(latest_user_msg)
            
            enhanced_system_prompt = system_prompt
            
            # 添加用户信息到系统提示
            if user_info:
                # 使用传入的 user_info_manager 实例
                user_info_str = self.user_info_manager.format_user_info(user_info)
                if user_info_str != "暂无用户信息":
                    enhanced_system_prompt = f"{enhanced_system_prompt}\n\n{user_info_str}\n请根据用户的个人情况和案件信息，提供针对性的法律建议。"
            
            # 添加国家法律法规数据库结果
            if national_laws.get("success") and national_laws.get("list"):
                law_context = "\n\n**【国家法律法规数据库检索结果】**\n"
                for law in national_laws.get("list", [])[:3]:
                    law_context += f"\n### 📜 {law.get('title', '未知标题')}\n"
                    law_context += f"{law.get('content', law.get('summary', ''))}\n"
                    if law.get('url'):
                        law_context += f"\n🔗 查看原文：{law.get('url')}\n"
                enhanced_system_prompt += law_context
            
            # 构建消息列表
            full_messages = [{"Role": "system", "Content": enhanced_system_prompt}]
            
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                if role == "user" and content:
                    full_messages.append({"Role": "user", "Content": content})
                elif role == "assistant" and content:
                    full_messages.append({"Role": "assistant", "Content": content})
            
            # 确保最后一条消息是用户消息
            if not full_messages or full_messages[-1]["Role"] != "user":
                if latest_user_msg:
                    full_messages.append({"Role": "user", "Content": latest_user_msg})
            
            req.Messages = full_messages
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error in chat_with_history: {error_msg}")  # 调试信息
            if "InvalidParameter" in error_msg:
                try:
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
    .info-box {
        background-color: #f5f5f5;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #1f77b4;
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
    if "welcome_shown" not in st.session_state:  # 标记欢迎消息是否已显示
        st.session_state.welcome_shown = False
    if "mode" not in st.session_state:
        st.session_state.mode = "智能对话"  # 默认改为智能对话
    if "law_db" not in st.session_state:
        st.session_state.law_db = LocalLawDatabase()
    if "user_info_collected" not in st.session_state:
        st.session_state.user_info_collected = {}
    if "collecting_info" not in st.session_state:
        st.session_state.collecting_info = True
    if "info_step" not in st.session_state:
        st.session_state.info_step = 0
    if "user_info_manager" not in st.session_state:
        st.session_state.user_info_manager = UserInfoManager()

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
            st.session_state.welcome_shown = False
            st.session_state.collecting_info = True
            st.session_state.user_info_collected = {}
            st.rerun()
    
    st.markdown("---")
    
    # 用户信息显示（仅在登录后且非收集状态显示）
    if st.session_state.hy_client is not None and not st.session_state.collecting_info:
        st.markdown("### 👤 用户信息")
        if st.session_state.user_info_collected:
            for key, value in st.session_state.user_info_collected.items():
                if value and key != "phone" and key != "email" and key != "address":
                    st.caption(f"**{key}**: {value}")
            if st.button("✏️ 修改信息", use_container_width=True):
                st.session_state.collecting_info = True
                st.session_state.info_step = 0
                st.rerun()
        else:
            st.info("暂无用户信息")
            if st.button("📝 填写信息", use_container_width=True):
                st.session_state.collecting_info = True
                st.rerun()
        
        st.markdown("---")
    
    # 模式选择（仅在非收集状态显示）
    if st.session_state.hy_client is not None and not st.session_state.collecting_info:
        st.markdown("### 🎯 对话模式")
        mode_options = {
            "智能对话": "💬 智能对话",
            "法律解释": "📚 法律解释",
            "节点提醒": "⏰ 节点提醒", 
            "文书生成": "📄 文书生成"
        }
        
        cols = st.columns(2)
        for i, (mode_key, mode_label) in enumerate(mode_options.items()):
            col = cols[i % 2]
            with col:
                if st.button(mode_label, key=f"mode_{mode_key}", use_container_width=True):
                    st.session_state.mode = mode_key
                    st.rerun()
        
        st.markdown(f"**当前模式：** `{st.session_state.mode}`")
        
        st.markdown("---")
        
        # 对话控制
        st.markdown("### 🛠️ 对话控制")
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.welcome_shown = False
            st.rerun()
    
    st.markdown("---")
    
    # 使用帮助
    with st.expander("ℹ️ 使用帮助"):
        st.markdown("""
        **功能介绍：**
        - 💬 **智能对话**：日常法律咨询，通俗解释
        - 📚 **法律解释**：解读法律条文，匹配相关法条
        - ⏰ **节点提醒**：输入您的案件情况，获取法律流程节点和具体时间提醒
        - 📄 **文书生成**：生成标准法律文书（起诉状、答辩状等）
        
        **数据来源：**
        - 🏛️ **国家法律法规数据库**（全国人大官网）
        
        **使用技巧：**
        - 首次使用需填写基本信息以获得个性化服务
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
                            cli = HunyuanClient(secret_id, secret_key, st.session_state.law_db, st.session_state.user_info_manager)
                            test_result = cli.chat("测试连接", "你只需回复'正常'")
                            st.session_state.hy_client = cli
                            st.success("✅ 登录成功！已连接国家法律法规数据库")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 登录失败：{str(e)}")
    
    st.stop()

# ===================== 用户信息收集界面 =====================
if st.session_state.collecting_info:
    st.markdown("## 📋 个人信息收集")
    st.markdown("为了给您提供更精准的法律建议，请先填写以下信息（可选择性填写）：")
    
    # 信息收集步骤
    steps = ["基本信息", "案件信息", "联系方式"]
    current_step = st.session_state.info_step
    
    # 步骤指示器
    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if i < current_step:
                st.markdown(f"✅ ~~{step}~~")
            elif i == current_step:
                st.markdown(f"**🔵 {step}**")
            else:
                st.markdown(f"⚪ {step}")
    
    st.markdown("---")
    
    if current_step == 0:
        with st.form(key="info_form_step_0"):
            st.markdown("### 基本信息")
            name = st.text_input("姓名/称呼", value=st.session_state.user_info_collected.get("name", ""))
            age = st.text_input("年龄", value=st.session_state.user_info_collected.get("age", ""))
            occupation = st.text_input("职业", value=st.session_state.user_info_collected.get("occupation", ""))
            
            education_options = ["", "小学", "初中", "高中/中专", "大专", "本科", "硕士", "博士"]
            current_edu = st.session_state.user_info_collected.get("education", "")
            edu_index = education_options.index(current_edu) if current_edu in education_options else 0
            education = st.selectbox("学历", education_options, index=edu_index)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col3:
                next_btn = st.form_submit_button("下一步 →", use_container_width=True)
            with col2:
                skip_btn = st.form_submit_button("跳过", use_container_width=True)
            
            if next_btn or skip_btn:
                if name: st.session_state.user_info_collected["name"] = name
                if age: st.session_state.user_info_collected["age"] = age
                if occupation: st.session_state.user_info_collected["occupation"] = occupation
                if education: st.session_state.user_info_collected["education"] = education
                st.session_state.info_step = 1
                st.rerun()
    
    elif current_step == 1:
        with st.form(key="info_form_step_1"):
            st.markdown("### 案件信息")
            
            case_options = ["", "离婚纠纷", "合同纠纷", "劳动纠纷", "侵权纠纷", "继承纠纷", "房产纠纷", "消费者权益纠纷", "其他"]
            current_case = st.session_state.user_info_collected.get("case_type", "")
            case_index = case_options.index(current_case) if current_case in case_options else 0
            case_type = st.selectbox("案件类型", case_options, index=case_index)
            
            role_options = ["", "原告", "被告", "申请人", "被申请人", "其他"]
            current_role = st.session_state.user_info_collected.get("case_role", "")
            role_index = role_options.index(current_role) if current_role in role_options else 0
            case_role = st.selectbox("您在案件中的角色", role_options, index=role_index)
            
            incident_date = st.date_input("事件发生时间", value=None)
            current_status = st.text_area("当前进展状态", value=st.session_state.user_info_collected.get("current_status", ""),
                                         placeholder="例如：已协商未果、已起诉、等待开庭等")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                prev_btn = st.form_submit_button("← 上一步", use_container_width=True)
            with col3:
                next_btn = st.form_submit_button("下一步 →", use_container_width=True)
            with col2:
                skip_btn = st.form_submit_button("跳过", use_container_width=True)
            
            if prev_btn:
                st.session_state.info_step = 0
                st.rerun()
            elif next_btn or skip_btn:
                if case_type: st.session_state.user_info_collected["case_type"] = case_type
                if case_role: st.session_state.user_info_collected["case_role"] = case_role
                if incident_date: st.session_state.user_info_collected["incident_date"] = str(incident_date)
                if current_status: st.session_state.user_info_collected["current_status"] = current_status
                st.session_state.info_step = 2
                st.rerun()
    
    elif current_step == 2:
        with st.form(key="info_form_step_2"):
            st.markdown("### 联系方式（可选）")
            st.caption("以下信息仅用于联系，不会公开")
            
            phone = st.text_input("联系电话", value=st.session_state.user_info_collected.get("phone", ""))
            email = st.text_input("电子邮箱", value=st.session_state.user_info_collected.get("email", ""))
            address = st.text_input("通讯地址", value=st.session_state.user_info_collected.get("address", ""))
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                prev_btn = st.form_submit_button("← 上一步", use_container_width=True)
            with col3:
                complete_btn = st.form_submit_button("✅ 完成并开始咨询", use_container_width=True)
            
            if prev_btn:
                st.session_state.info_step = 1
                st.rerun()
            elif complete_btn:
                if phone: st.session_state.user_info_collected["phone"] = phone
                if email: st.session_state.user_info_collected["email"] = email
                if address: st.session_state.user_info_collected["address"] = address
                st.session_state.collecting_info = False
                st.rerun()
    
    # 显示已收集的信息摘要
    if st.session_state.user_info_collected:
        st.markdown("---")
        st.markdown("### 📝 已填写信息摘要")
        cols = st.columns(3)
        info_items = [(k, v) for k, v in st.session_state.user_info_collected.items() if v]
        for i, (key, value) in enumerate(info_items):
            with cols[i % 3]:
                st.info(f"**{key}**: {value}")
    
    st.stop()

# ===================== 节点提醒模式 =====================
if st.session_state.mode == "节点提醒":
    st.markdown("## ⏰ 法律流程节点提醒")
    st.markdown("请填写您的案件情况，系统将为您分析法律流程节点和具体时间提醒")
    
    # 如果有用户信息，自动预填
    default_case_type = st.session_state.user_info_collected.get("case_type", "离婚纠纷")
    default_case_details = st.session_state.user_info_collected.get("current_status", "")
    
    with st.form("node_reminder_form"):
        case_options = ["离婚纠纷", "合同纠纷", "劳动纠纷", "侵权纠纷", "继承纠纷", "房产纠纷", "消费者权益纠纷", "其他"]
        current_index = case_options.index(default_case_type) if default_case_type in case_options else 0
        case_type = st.selectbox("案件类型", case_options, index=current_index)
        
        case_details = st.text_area(
            "案件详情", 
            value=default_case_details,
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
                        # 整合用户信息到分析中
                        user_context = ""
                        if st.session_state.user_info_collected:
                            user_context = f"\n\n用户背景：\n"
                            if st.session_state.user_info_collected.get("case_role"):
                                user_context += f"- 角色：{st.session_state.user_info_collected.get('case_role')}\n"
                            if st.session_state.user_info_collected.get("incident_date"):
                                user_context += f"- 事发时间：{st.session_state.user_info_collected.get('incident_date')}\n"
                        
                        full_details = case_details + user_context
                        result = st.session_state.hy_client.process_node_reminder(case_type, full_details)
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
    
    # 从用户信息中获取默认值
    default_name = st.session_state.user_info_collected.get("name", "")
    default_role = st.session_state.user_info_collected.get("case_role", "")
    
    with st.form("document_form"):
        if doc_type == "起诉状":
            plaintiff_default = f"{default_name}" if default_name else ""
            plaintiff = st.text_area("原告信息", value=plaintiff_default, 
                                    placeholder="姓名、性别、身份证号、住址、联系方式等")
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
            defendant_default = f"{default_name}" if default_role == "被告" else ""
            defendant = st.text_area("被告信息", value=defendant_default,
                                    placeholder="姓名、性别、身份证号、住址、联系方式等")
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
            applicant_default = f"{default_name}" if default_name else ""
            applicant = st.text_area("申请人信息", value=applicant_default,
                                    placeholder="姓名、性别、身份证号、住址、联系方式等")
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

# ===================== 智能对话主聊天区域 =====================
# 显示欢迎消息（仅当没有对话历史且未显示过欢迎消息时）
if not st.session_state.messages and not st.session_state.welcome_shown:
    # 根据用户信息生成个性化欢迎消息
    user_name = st.session_state.user_info_collected.get("name", "用户")
    case_type = st.session_state.user_info_collected.get("case_type", "")
    case_role = st.session_state.user_info_collected.get("case_role", "")
    
    welcome_msg = f"""
您好，{user_name}！我是司法流程辅助系统的智能助手。👋

"""
    if case_type and case_role:
        welcome_msg += f"""
根据您填写的信息，我了解到您正在处理**{case_type}**案件，您的角色是**{case_role}**。

我将基于这些信息为您提供针对性的法律建议和流程指导。

"""
    else:
        welcome_msg += """
为了更好地为您服务，我建议您先完善个人信息（点击侧边栏的"修改信息"按钮）。

"""
    
    welcome_msg += """
您可以：
- 📚 询问具体法律条文的解释
- ⚖️ 咨询法律程序和流程
- 📝 了解相关案例和判例
- 💡 获取维权建议和策略

请随时向我提问，我会结合您的具体情况，为您提供专业的法律建议！
"""
    
    with st.chat_message("assistant"):
        st.markdown(welcome_msg)
    
    st.session_state.welcome_shown = True

# 显示对话历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入框
prompt = st.chat_input("请输入您的法律问题，系统将结合您的个人信息提供针对性建议...")
if prompt:
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 系统提示词（结合用户信息）
    system_prompts = {
        "法律解释": f"""你是专业法律科普助手。

{st.session_state.user_info_manager.format_user_info(st.session_state.user_info_collected)}

请根据用户的个人情况和案件背景，结合国家法律法规数据库的官方条文，提供针对性的法律解读。
回答中请注明法律条文来源，必要时提供官方链接。
回答要通俗易懂，如果用户是特定角色（如原告、被告），要从该角色的角度给出建议。""",

        "智能对话": f"""你是专业的法律顾问。

{st.session_state.user_info_manager.format_user_info(st.session_state.user_info_collected)}

请根据用户的个人情况和案件背景，结合国家法律法规，用通俗易懂的语言解答法律问题。
优先引用官方法律条文，提供针对用户具体情况的建议。
要考虑用户的案件类型、角色和当前状态，给出切实可行的建议。"""
    }
    
    system_prompt = system_prompts.get(st.session_state.mode, system_prompts["智能对话"])
    
    # 获取AI回复
    with st.chat_message("assistant"):
        with st.spinner("🔍 正在检索国家法律法规数据库并分析您的个人情况..."):
            try:
                # 传入完整的历史消息和用户信息（只传递真正的对话历史）
                # 注意：st.session_state.messages 已经包含了刚添加的用户消息
                history = st.session_state.messages[:-1]  # 获取除了最后一条用户消息外的所有历史
                
                response = st.session_state.hy_client.chat_with_history(
                    history,
                    system_prompt,
                    st.session_state.user_info_collected
                )
                
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
