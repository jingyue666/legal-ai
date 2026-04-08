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
                "le":tit "中华人民共和国民法典·继承编",
                "content": """**第一千一百二十七条** 遗产按照下列顺序继承：
(一)第一顺序：配偶、子女、父母；
(二)第二顺序：兄弟姐妹、祖父母、外祖父母。
继承开始后由第一顺序继承人，继承，第二顺序继承人不继承；没有第一顺序继承人继承的，由第二顺序继承人继承。

**第一千一百三十条** 同一顺序继承人继承遗产的份额，一般应当均等。
对生活有特殊困难又缺乏劳动能力的继承人，分配遗产时，应当予以照顾。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            }
        }
    
   def search_laws(self, ke yword: str, law_type: str = "all", page: int = 1, page_size: int = 10) -> Dict:
        """搜索法律法规"""
        matched_laws = self._search_from_preset(keyword)
        
        if matched_laws:
            return {
                "success": True,
                "total": len(matched_laws),
                "list": matched_laws,
                "keyword": keyword,
                "source": "法律知识库"
            }
        
        try:
            params = {
                "keyword": keyword,
                "page": page,
                "pageSize": page_size,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(self.search_url, params=params, headers=headers,meout=5)
         ti    
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
    
    def _search_from_preset(self, keyword: str) -> List:
        """从预设知识库搜索"""
        results = []
        keyword_lower = keyword.lower()
        
        for key, law in self.law_summaries.items():
            if key in keyword_lower or keyword_lower in key:
                results.append({
                    "id": key,
                    "title": law["title"],
                    "content": law["content"],
                    "url": law["url"]
                })
                
        return results
    
    def _parse_search_results(self, results_list: List) -> List:
        """解析搜索结果"""
        parsed_results = []
        for item in results_list:
            parsed_results.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "content": item.get("content", ""),
                "url": item.get("url")
            })
        return parsed_results
    
    def _get_empty_result(self, keyword: str) -> Dict:
        """返回空结果"""
        return {
            "success": False,
            "total": 0,
            "list": [],
            "keyword": keyword,
            "source": "国家法律法规数据库",
            "message": "未找到相关法律法规"
        }

# ===================== 腾讯云混元大模型接口模块 =====================
class HunYuanLLM:
    """腾讯云混元大模型接口类"""
    
    def __init__(self, secret_id: str, secret_key: str):
        """初始化客户端"""
        self.cred = credential.Credential(secret_id, secret_key)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "hunyuan.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        self.client = hunyuan_client.HunyuanClient(self.cred, "ap-guangzhou", clientProfile)
    
    def generate_text(self, prompt: str, model: str = "hunyuan-pro", temperature: float = 0.7) -> str:
        """生成文本"""
        req = models.ChatCompletionsRequest()
        req.Model = model
        req.Messages = [
            {
                "Role": "user",
                "Content": prompt
            }
        ]
        req.Temperature = temperature
        
        try:
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            return f"调用混元大模型失败: {str(e)}"

# ===================== 司法流程辅助与节点提醒系统主类 =====================
class LegalProcessAssistant:
    """司法流程辅助与节点提醒系统"""
    
    def __init__(self, llm_api_key: str, llm_secret_id: str):
        """初始化系统"""
        self.law_db = NationalLawDatabase()
        self.llm = HunYuanLLM(llm_api_key, llm_secret_id)
        self.case_history = {}
    
    def analyze_case(self, case_description: str) -> Dict:
        """分析案件并提供建议"""
        # 识别案件类型
        case_type = self._identify_case_type(case_description)
        
        # 获取相关法律条文
        legal_info = self.law_db.search_laws(case_type)
        
        # 构建提示词
        prompt = self._build_prompt(case_description, case_type, legal_info)
        
        # 调用大模型获取建议
        advice = self.llm.generate_text(prompt)
        
        # 提取关键节点
        nodes = self._extract_key_nodes(advice, case_type)
        
        # 保存案件历史
        case_id = f"case_{int(time.time())}"
        self.case_history[case_id] = {
            "description": case_description,
            "type": case_type,
            "legal_info": legal_info,
            "advice": advice,
            "nodes": nodes,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return {
            "case_id": case_id,
            "case_type": case_type,
            "legal_info": legal_info,
            "advice": advice,
            "nodes": nodes
        }
    
    def _identify_case_type(self, description: str) -> str:
        """识别案件类型"""
        keywords = {
            "离婚": ["离婚", "分居", "感情破裂", "家庭纠纷"],
            "结婚": ["结婚", "婚姻登记", "彩礼", "婚前财产"],
            "合同": ["合同", "违约", "条款", "协议", "买卖"],
            "劳动": ["劳动", "工伤", "裁员", "试用期", "工资"],
            "侵权": ["侵权", "损害", "赔偿", "精神损害"],
            "继承": ["继承", "遗产", "遗嘱", "继承人"]
        }
        
        for case_type, words in keywords.items():
            for word in words:
                if word in description:
                    return case_type
        
        return "其他"
    
    def _build_prompt(self, description: str, case_type: str, legal_info: Dict) -> str:
        """构建提示词"""
        legal_content = ""
        if legal_info.get("success") and legal_info.get("list"):
            legal_content = "\n\n".join([
                f"{item['title']}:\n{item['content'][:200]}..." 
                for item in legal_info["list"][:2]
            ])
        else:
            legal_content = "未找到相关法律条文，请依据常识和法律原则提供建议。"
        
        return f"""作为一名专业的法律助手，请针对以下{case_type}案件提供详细分析和建议：

案件描述：{description}

相关法律条文：
{legal_content}

请提供以下内容：
1. 案件性质与法律依据
2. 可能的诉讼策略或解决方案
3. 关键时间节点与注意事项
4. 证据准备建议
"""
    
    def _extract_key_nodes(self, advice: str, case_type: str) -> List[Dict]:
        """提取关键节点"""
        nodes = []
        
        # 使用正则表达式查找日期信息
        date_pattern = r"(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}[日]?)|(\d{1,2}[月/-]\d{1,2}[日])"
        dates = re.findall(date_pattern, advice)
        
        # 使用正则表达式查找时间周期
        period_pattern = r"(\d+)天|(\d+)月|(\d+)年|(\d+)个工作日"
        periods = re.findall(period_pattern, advice)
        
        # 查找关键阶段描述
        stage_pattern = r"(起诉|立案|送达|举证|调解|开庭|判决|执行|上诉)"
        stages = re.findall(stage_pattern, advice)
        
        # 合并找到的节点
        all_dates = [d[0] if d[0] else d[1] for d in dates]
        all_periods = [p[0] if p[0] else p[1] if p[1] else p[2] if p[2] else p[3] for p in periods]
        
        # 添加日期节点
        for i, date in enumerate(all_dates[:3]):  # 限制最多3个日期节点
            nodes.append({
                "type": "日期",
                "description": f"关键日期{i+1}",
                "value": date,
                "priority": 2
            })
        
        # 添加期限节点
        for i, period in enumerate(all_periods[:3]):  # 限制最多3个期限节点
            nodes.append({
                "type": "期限",
                "description": f"关键期限{i+1}",
                "value": period,
                "priority": 2
            })
        
        # 添加阶段节点
        for i, stage in enumerate(stages[:5]):  # 限制最多5个阶段节点
            nodes.append({
                "type": "阶段",
                "description": f"诉讼阶段{i+1}",
                "value": stage,
                "priority": 1
            })
        
        # 如果没有找到任何节点，添加默认节点
        if not nodes:
            nodes.append({
                "type": "提示",
                "description": "无明确时间节点",
                "value": "请联系专业律师获取更详细的时间安排",
                "priority": 3
            })
        
        return nodes
    
    def get_case_reminders(self, case_id: str) -> List[Dict]:
        """获取案件提醒节点"""
        if case_id in self.case_history:
            return self.case_history[case_id]["nodes"]
        return []

# ===================== Streamlit 应用界面 =====================
def main():
    st.set_page_config(
        page_title="司法流程辅助与节点提醒系统",
        page_icon="⚖️",
        layout="wide"
    )
    
    st.title("⚖️ 司法流程辅助与节点提醒系统")
    st.markdown("""
    > 本系统提供法律案件分析与流程节点提醒功能，结合国家法律法规数据库与腾讯云混元大模型，为您提供专业的法律支持。
    """)
    
    # 侧边栏配置
    with st.sidebar:
        st.header("🔑 API 配置")
        llm_secret_id = st.text_input("腾讯云 SecretId", type="password")
        llm_secret_key = st.text_input("腾讯云 SecretKey", type="password")
        
        if not llm_secret_id or not llm_secret_key:
            st.warning("请输入腾讯云API密钥以启用智能分析功能")
    
    # 检查API密钥是否配置
    api_configured = bool(llm_secret_id and llm_secret_key)
    
    # 创建系统实例
    system = None
    if api_configured:
        system = LegalProcessAssistant(llm_secret_id, llm_secret_key)
    
    # 创建选项卡
    tab1, tab2, tab3 = st.tabs(["📝 案件分析", "📅 节点提醒", "📚 法律查询"])
    
    # 案件分析选项卡
    with tab1:
        st.header("案件分析")
        case_description = st.text_area("请输入案件描述", height=150)
        
        if st.button("分析案件", disabled=not api_configured):
            if not case_description:
                st.error("请输入案件描述")
            else:
                with st.spinner("正在分析中..."):
                    result = system.analyze_case(case_description)
                    
                    st.success("分析完成！")
                    
                    # 显示案件类型
                    st.subheader(f"📋 案件类型: {result['case_type']}")
                    
                    # 显示法律条文
                    with st.expander("📜 相关法律条文"):
                        if result["legal_info"]["success"]:
                            for item in result["legal_info"]["list"]:
                                st.markdown(f"### {item['title']}")
                                st.markdown(item["content"])
                                st.markdown(f"[查看详情]({item['url']})")
                        else:
                            st.info(result["legal_info"].get("message", "未找到相关法律条文"))
                    
                    # 显示分析结果
                    st.subheader("💡 分析与建议")
                    st.markdown(result["advice"])
                    
                    # 保存案件ID到会话状态
                    st.session_state["current_case_id"] = result["case_id"]
    
    # 节点提醒选项卡
    with tab2:
        st.header("节点提醒")
        
        # 获取所有案件ID
        case_ids = list(system.case_history.keys()) if api_configured else []
        
        if not case_ids:
            st.info("暂无案件记录，请先在案件分析页面提交案件")
        else:
            selected_case_id = st.selectbox("选择案件", case_ids)
            
            if selected_case_id:
                reminders = system.get_case_reminders(selected_case_id)
                
                if not reminders:
                    st.info("该案件暂无节点提醒")
                else:
                    st.subheader(f"📅 {selected_case_id} 的节点提醒")
                    
                    # 按优先级排序
                    sorted_reminders = sorted(reminders, key=lambda x: x["priority"])
                    
                    for reminder in sorted_reminders:
                        if reminder["type"] == "日期":
                            st.markdown(f"- 🗓️ **{reminder['description']}**: {reminder['value']}")
                        elif reminder["type"] == "期限":
                            st.markdown(f"- ⏳ **{reminder['description']}**: {reminder['value']}")
                        elif reminder["type"] == "阶段":
                            st.markdown(f"- 📌 **{reminder['description']}**: {reminder['value']}")
                        else:
                            st.markdown(f"- ℹ️ **{reminder['description']}**: {reminder['value']}")
                        
                        # 添加提醒设置
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            note = st.text_input(f"备注 ({reminder['description']})", key=f"note_{selected_case_id}_{reminder['description']}")
                        with col2:
                            if st.button("设置提醒", key=f"remind_{selected_case_id}_{reminder['description']}"):
                                st.success(f"已为 {reminder['description']} 设置提醒")
    
    # 法律查询选项卡
    with tab3:
        st.header("法律查询")
        search_keyword = st.text_input("输入关键词（如离婚、合同、劳动等）")
        
        if st.button("搜索", disabled=not api_configured):
            if not search_keyword:
                st.error("请输入搜索关键词")
            else:
                with st.spinner("正在搜索..."):
                    result = system.law_db.search_laws(search_keyword)
                    
                    if result["success"]:
                        st.success(f"找到 {result['total']} 条相关法规")
                        
                        for item in result["list"]:
                            with st.expander(f"{item['title']}"):
                                st.markdown(item["content"])
                                if item["url"]:
                                    st.markdown(f"[查看原文]({item['url']})")
                    else:
                        st.info(result.get("message", "未找到相关法规"))

if __name__ == "__main__":
    main()
