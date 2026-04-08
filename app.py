import streamlit as st
import time
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

# 尝试导入腾讯云SDK
try:
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
    TENCENT_AVAILABLE = True
except ImportError:
    TENCENT_AVAILABLE = False

# 尝试导入requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

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
(五)其他导致夫妻感情破裂的情形。

**第一千零八十四条** 父母与子女间的关系，不因父母离婚而消除。离婚后，子女无论由父或者母直接抚养，仍是父母双方的子女。
离婚后，父母对于子女仍有抚养、教育、保护的权利和义务。
离婚后，不满两周岁的子女，以由母亲直接抚养为原则。已满两周岁的子女，父母双方对抚养问题协议不成的，由人民法院根据双方的具体情况，按照最有利于未成年子女的原则判决。子女已满八周岁的，应当尊重其真实意愿。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "结婚": {
                "title": "中华人民共和国民法典·婚姻家庭编",
                "content": """**第一千零四十六条** 结婚应当男女双方完全自愿，禁止任何一方对另一方加以强迫，禁止任何组织或者个人加以干涉。

**第一千零四十七条** 结婚年龄，男不得早于二十二周岁，女不得早于二十周岁。

**第一千零四十八条** 直系血亲或者三代以内的旁系血亲禁止结婚。

**第一千零四十九条** 要求结婚的男女双方应当亲自到婚姻登记机关申请结婚登记。符合本法规定的，予以登记，发给结婚证。完成结婚登记，即确立婚姻关系。

**第一千零五十一条** 有下列情形之一的，婚姻无效：
(一)重婚；
(二)有禁止结婚的亲属关系；
(三)未到法定婚龄。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "合同": {
                "title": "中华人民共和国民法典·合同编",
                "content": """**第四百六十九条** 当事人订立合同，可以采用书面形式、口头形式或者其他形式。

**第四百七十条** 合同的内容由当事人约定，一般包括下列条款：
(一)当事人的姓名或者名称和住所；
(二)标的；
(三)数量；
(四)质量；
(五)价款或者报酬；
(六)履行期限、地点和方式；
(七)违约责任；
(八)解决争议的方法。

**第五百七十七条** 当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。

**第五百七十八条** 当事人一方明确表示或者以自己的行为表明不履行合同义务的，对方可以在履行期限届满前请求其承担违约责任。

**第五百八十四条** 当事人一方不履行合同义务或者履行合同义务不符合约定，造成对方损失的，损失赔偿额应当相当于因违约所造成的损失，包括合同履行后可以获得的利益。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "违约": {
                "title": "中华人民共和国民法典·合同编",
                "content": """**第五百七十七条** 当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。

**第五百八十五条** 当事人可以约定一方违约时应当根据违约情况向对方支付一定数额的违约金，也可以约定因违约产生的损失赔偿额的计算方法。

约定的违约金低于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以增加；约定的违约金过分高于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以适当减少。

**第五百八十六条** 当事人可以约定一方向对方给付定金作为债权的担保。定金合同自实际交付定金时成立。
定金的数额由当事人约定；但是，不得超过主合同标的额的百分之二十，超过部分不产生定金的效力。实际交付的定金数额多于或者少于约定数额的，视为变更约定的定金数额。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "劳动": {
                "title": "中华人民共和国劳动合同法",
                "content": """**第十条** 建立劳动关系，应当订立书面劳动合同。
已建立劳动关系，未同时订立书面劳动合同的，应当自用工之日起一个月内订立书面劳动合同。

**第十九条** 劳动合同期限三个月以上不满一年的，试用期不得超过一个月；劳动合同期限一年以上不满三年的，试用期不得超过二个月；三年以上固定期限和无固定期限的劳动合同，试用期不得超过六个月。

**第三十九条** 劳动者有下列情形之一的，用人单位可以解除劳动合同：
(一)在试用期间被证明不符合录用条件的；
(二)严重违反用人单位的规章制度的；
(三)严重失职，营私舞弊，给用人单位造成重大损害的；
(四)劳动者同时与其他用人单位建立劳动关系，对完成本单位的工作任务造成严重影响，或者经用人单位提出，拒不改正的；
(五)因本法第二十六条第一款第一项规定的情形致使劳动合同无效的；
(六)被依法追究刑事责任的。

**第四十七条** 经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资。六个月以上不满一年的，按一年计算；不满六个月的，向劳动者支付半个月工资的经济补偿。

**第八十七条** 用人单位违反本法规定解除或者终止劳动合同的，应当依照本法第四十七条规定的经济补偿标准的二倍向劳动者支付赔偿金。""",
                "url": "https://flk.npc.gov.cn/detail/劳动合同法"
            },
            "工资": {
                "title": "中华人民共和国劳动合同法",
                "content": """**第八十五条** 用人单位有下列情形之一的，由劳动行政部门责令限期支付劳动报酬、加班费或者经济补偿；劳动报酬低于当地最低工资标准的，应当支付其差额部分；逾期不支付的，责令用人单位按应付金额百分之五十以上百分之一百以下的标准向劳动者加付赔偿金：
(一)未按照劳动合同的约定或者国家规定及时足额支付劳动者劳动报酬的；
(二)低于当地最低工资标准支付劳动者工资的；
(三)安排加班不支付加班费的；
(四)解除或者终止劳动合同，未依照本法规定给予经济补偿的。

**《中华人民共和国劳动法》第五十条** 工资应当以货币形式按月支付给劳动者本人。不得克扣或者无故拖欠劳动者的工资。""",
                "url": "https://flk.npc.gov.cn/detail/劳动合同法"
            },
            "加班": {
                "title": "中华人民共和国劳动法",
                "content": """**第四十四条** 有下列情形之一的，用人单位应当按照下列标准支付高于劳动者正常工作时间工资的工资报酬：
(一)安排劳动者延长工作时间的，支付不低于工资的百分之一百五十的工资报酬；
(二)休息日安排劳动者工作又不能安排补休的，支付不低于工资的百分之二百的工资报酬；
(三)法定休假日安排劳动者工作的，支付不低于工资的百分之三百的工资报酬。

**第四十一条** 用人单位由于生产经营需要，经与工会和劳动者协商后可以延长工作时间，一般每日不得超过一小时；因特殊原因需要延长工作时间的，在保障劳动者身体健康的条件下延长工作时间每日不得超过三小时，但是每月不得超过三十六小时。""",
                "url": "https://flk.npc.gov.cn/detail/劳动法"
            },
            "侵权": {
                "title": "中华人民共和国民法典·侵权责任编",
                "content": """**第一千一百六十五条** 行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。
依照法律规定推定行为人有过错，其不能证明自己没有过错的，应当承担侵权责任。

**第一千一百六十七条** 侵权行为危及他人人身、财产安全的，被侵权人有权请求侵权人承担停止侵害、排除妨碍、消除危险等侵权责任。

**第一千一百七十九条** 侵害他人造成人身损害的，应当赔偿医疗费、护理费、交通费、营养费、住院伙食补助费等为治疗和康复支出的合理费用，以及因误工减少的收入。

**第一千一百八十三条** 侵害自然人人身权益造成严重精神损害的，被侵权人有权请求精神损害赔偿。

**第一千一百八十四条** 侵害他人财产的，财产损失按照损失发生时的市场价格或者其他合理方式计算。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "继承": {
                "title": "中华人民共和国民法典·继承编",
                "content": """**第一千一百二十七条** 遗产按照下列顺序继承：
(一)第一顺序：配偶、子女、父母；
(二)第二顺序：兄弟姐妹、祖父母、外祖父母。
继承开始后，由第一顺序继承人继承，第二顺序继承人不继承；没有第一顺序继承人继承的，由第二顺序继承人继承。

**第一千一百二十八条** 被继承人的子女先于被继承人死亡的，由被继承人的子女的直系晚辈血亲代位继承。
被继承人的兄弟姐妹先于被继承人死亡的，由被继承人的兄弟姐妹的子女代位继承。
代位继承人一般只能继承被代位继承人有权继承的遗产份额。

**第一千一百三十条** 同一顺序继承人继承遗产的份额，一般应当均等。
对生活有特殊困难又缺乏劳动能力的继承人，分配遗产时，应当予以照顾。
对被继承人尽了主要扶养义务或者与被继承人共同生活的继承人，分配遗产时，可以多分。
有扶养能力和有扶养条件的继承人，不尽扶养义务的，分配遗产时，应当不分或者少分。
继承人协商同意的，也可以不均等。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "房产": {
                "title": "中华人民共和国民法典·物权编",
                "content": """**第二百零九条** 不动产物权的设立、变更、转让和消灭，经依法登记，发生效力；未经登记，不发生效力，但是法律另有规定的除外。

**第二百一十四条** 不动产物权的设立、变更、转让和消灭，依照法律规定应当登记的，自记载于不动产登记簿时发生效力。

**第三百五十九条** 住宅建设用地使用权期限届满的，自动续期。续期费用的缴纳或者减免，依照法律、行政法规的规定办理。

**第七百零三条** 租赁合同是出租人将租赁物交付承租人使用、收益，承租人支付租金的合同。
**第七百零五条** 租赁期限不得超过二十年。超过二十年的，超过部分无效。
**第七百零七条** 租赁期限六个月以上的，应当采用书面形式。当事人未采用书面形式，无法确定租赁期限的，视为不定期租赁。""",
                "url": "https://flk.npc.gov.cn/detail/民法典"
            },
            "消费者": {
                "title": "中华人民共和国消费者权益保护法",
                "content": """**第五十五条** 经营者提供商品或者服务有欺诈行为的，应当按照消费者的要求增加赔偿其受到的损失，增加赔偿的金额为消费者购买商品的价款或者接受服务的费用的三倍；增加赔偿的金额不足五百元的，为五百元。

**第二十四条** 经营者提供的商品或者服务不符合质量要求的，消费者可以依照国家规定、当事人约定退货，或者要求经营者履行更换、修理等义务。

**第十一条** 消费者因购买、使用商品或者接受服务受到人身、财产损害的，享有依法获得赔偿的权利。

**第三十九条** 消费者和经营者发生消费者权益争议的，可以通过下列途径解决：
(一)与经营者协商和解；
(二)请求消费者协会或者依法成立的其他调解组织调解；
(三)向有关行政部门投诉；
(四)根据与经营者达成的仲裁协议提请仲裁机构仲裁；
(五)向人民法院提起诉讼。""",
                "url": "https://flk.npc.gov.cn/detail/消费者权益保护法"
            },
            "刑事": {
                "title": "中华人民共和国刑法",
                "content": """**第三条** 法律明文规定为犯罪行为的，依照法律定罪处刑；法律没有明文规定为犯罪行为的，不得定罪处刑。

**第五条** 刑罚的轻重，应当与犯罪分子所犯罪行和承担的刑事责任相适应。

**第十七条** 已满十六周岁的人犯罪，应当负刑事责任。
已满十四周岁不满十六周岁的人，犯故意杀人、故意伤害致人重伤或者死亡、强奸、抢劫、贩卖毒品、放火、爆炸、投放危险物质罪的，应当负刑事责任。
已满十二周岁不满十四周岁的人，犯故意杀人、故意伤害罪，致人死亡或者以特别残忍手段致人重伤造成严重残疾，情节恶劣，经最高人民检察院核准追诉的，应当负刑事责任。

**第二百六十四条** 盗窃公私财物，数额较大的，或者多次盗窃、入户盗窃、携带凶器盗窃、扒窃的，处三年以下有期徒刑、拘役或者管制，并处或者单处罚金；数额巨大或者有其他严重情节的，处三年以上十年以下有期徒刑，并处罚金；数额特别巨大或者有其他特别严重情节的，处十年以上有期徒刑或者无期徒刑，并处罚金或者没收财产。""",
                "url": "https://flk.npc.gov.cn/detail/刑法"
            }
        }
    
    def search_laws(self, keyword: str, law_type: str = "all", page: int = 1, page_size: int = 10) -> Dict:
        """搜索法律法规"""
        # 从预设知识库中匹配
        matched_laws = self._search_from_preset(keyword)
        
        if matched_laws:
            return {
                "success": True,
                "total": len(matched_laws),
                "list": matched_laws,
                "keyword": keyword,
                "source": "法律知识库"
            }
        
        # 尝试访问官网API
        if REQUESTS_AVAILABLE:
            try:
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
    
    def _search_from_preset(self, keyword: str) -> List:
        """从预设知识库搜索"""
        results = []
        keyword_lower = keyword.lower()
        
        # 精确匹配
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
        
        # 模糊匹配
        if not results:
            for key, law in self.law_summaries.items():
                for word in keyword_lower.split():
                    if len(word) >= 2 and word in key:
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
                        break
        
        return results
    
    def _parse_search_results(self, results: List) -> List:
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
    
    def _get_empty_result(self, keyword: str, error_msg: str = "") -> Dict:
        """返回空结果"""
        return {
            "success": False,
            "total": 0,
            "list": [],
            "keyword": keyword,
            "message": f"请访问国家法律法规数据库查询：https://flk.npc.gov.cn/"
        }
    
    def get_recommended_link(self, keyword: str) -> str:
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
            },
            "刑法": {
                "keywords": ["犯罪", "刑罚", "盗窃", "诈骗", "故意伤害"],
                "content": "《中华人民共和国刑法》是规定犯罪和刑罚的法律。"
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
    
    def search_law(self, query):
        """搜索相关法律知识"""
        results = []
        query_lower = query.lower()
        
        for law_name, law_data in self.laws.items():
            relevance = 0
            for keyword in law_data.get("keywords", []):
                if keyword in query:
                    relevance += 1
                elif keyword in query_lower:
                    relevance += 0.5
            
            if law_name in query:
                relevance += 2
            
            if relevance > 0:
                results.append({
                    "law_name": law_name,
                    "content": law_data.get("content", ""),
                    "relevance": relevance
                })
        
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:3]

# ===================== 混元AI客户端 =====================
class HunyuanClient:
    def __init__(self, secret_id=None, secret_key=None, law_db=None):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.law_db = law_db
        self.national_law_db = NationalLawDatabase()
        self.client = None
        self.use_demo = True
        
        # 尝试初始化腾讯云客户端
        if TENCENT_AVAILABLE and secret_id and secret_key:
            try:
                cred = credential.Credential(secret_id, secret_key)
                httpProfile = HttpProfile()
                httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
                clientProfile = ClientProfile()
                clientProfile.httpProfile = httpProfile
                self.client = hunyuan_client.HunyuanClient(cred, "ap-beijing", clientProfile)
                self.use_demo = False
            except Exception:
                self.use_demo = True
    
    def search_national_laws(self, keyword: str) -> Dict:
        """搜索国家法律法规数据库"""
        return self.national_law_db.search_laws(keyword)
    
    def chat(self, prompt, system_prompt):
        """通用对话接口"""
        # 先搜索法律知识
        national_laws = self.national_law_db.search_laws(prompt)
        
        # 演示模式
        if self.use_demo:
            return self._demo_chat(prompt, system_prompt, national_laws)
        
        # 正式模式
        try:
            enhanced_system_prompt = self._build_enhanced_prompt(system_prompt, prompt, national_laws)
            
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            req.Messages = [
                {"Role": "system", "Content": enhanced_system_prompt},
                {"Role": "user", "Content": prompt}
            ]
            req.Temperature = 0.7
            
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
            
        except Exception as e:
            return self._fallback_response(prompt, national_laws, str(e))
    
    def chat_with_history(self, messages, system_prompt):
        """支持多轮对话"""
        # 获取最新的用户消息
        latest_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                latest_user_msg = msg["content"]
                break
        
        # 搜索法律知识
        national_laws = self.national_law_db.search_laws(latest_user_msg)
        
        # 演示模式
        if self.use_demo:
            return self._demo_chat(latest_user_msg, system_prompt, national_laws)
        
        # 正式模式
        try:
            enhanced_system_prompt = self._build_enhanced_prompt(system_prompt, latest_user_msg, national_laws)
            
            # 构建消息列表
            full_messages = [{"Role": "system", "Content": enhanced_system_prompt}]
            
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    full_messages.append({"Role": "user", "Content": content})
                elif role == "assistant":
                    full_messages.append({"Role": "assistant", "Content": content})
            
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            req.Messages = full_messages
            req.Temperature = 0.7
            
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
            
        except Exception as e:
            return self._fallback_response(latest_user_msg, national_laws, str(e))
    
    def _build_enhanced_prompt(self, system_prompt, query, national_laws):
        """构建增强的系统提示词"""
        enhanced = system_prompt
        
        if national_laws.get("success") and national_laws.get("list"):
            law_context = "\n\n**【相关法律条文】**\n"
            for law in national_laws.get("list", [])[:3]:
                law_context += f"\n### {law.get('title', '法律条文')}\n"
                law_context += f"{law.get('content', law.get('summary', ''))}\n"
                if law.get('url'):
                    law_context += f"\n🔗 原文链接：{law.get('url')}\n"
            enhanced += law_context + "\n请基于以上法律条文回答用户问题。"
        
        return enhanced
    
    def _demo_chat(self, prompt, system_prompt, national_laws):
        """演示模式对话"""
        response = ""
        
        # 添加法律条文
        if national_laws.get("success") and national_laws.get("list"):
            response += "📚 **相关法律条文**\n\n"
            for law in national_laws.get("list", [])[:2]:
                response += f"### {law.get('title', '法律条文')}\n\n"
                response += f"{law.get('content', law.get('summary', ''))}\n\n"
                if law.get('url'):
                    response += f"🔗 [查看原文]({law.get('url')})\n\n"
                response += "---\n\n"
        
        # 添加法律分析
        response += "📝 **法律分析**\n\n"
        response += self._generate_analysis(prompt, national_laws)
        
        # 添加演示提示
        response += "\n\n---\n💡 **提示**：当前为演示模式。如需完整功能，请配置腾讯云密钥。"
        
        return response
    
    def _generate_analysis(self, prompt, national_laws):
        """生成法律分析"""
        prompt_lower = prompt.lower()
        
        if "离婚" in prompt_lower:
            return "根据《民法典》第1079条，离婚需要感情确已破裂。建议：\n1. 先尝试协议离婚\n2. 协商子女抚养权归属\n3. 分割夫妻共同财产\n4. 如无法协商，可向法院起诉"
        elif "合同" in prompt_lower or "违约" in prompt_lower:
            return "根据《民法典》合同编，违约方需承担：\n1. 继续履行合同义务\n2. 采取补救措施\n3. 赔偿实际损失\n4. 支付约定的违约金"
        elif "劳动" in prompt_lower or "工资" in prompt_lower:
            return "根据《劳动合同法》：\n1. 用人单位应按时足额支付工资\n2. 违法解除合同需支付双倍赔偿\n3. 经济补偿按工作年限计算\n4. 可向劳动监察部门投诉或申请劳动仲裁"
        elif "侵权" in prompt_lower:
            return "根据《民法典》侵权责任编：\n1. 侵权人需赔偿实际损失\n2. 包括医疗费、误工费、护理费等\n3. 造成严重精神损害的，可主张精神损害赔偿\n4. 建议收集证据，及时维权"
        elif "继承" in prompt_lower:
            return "根据《民法典》继承编：\n1. 遗产按法定顺序继承\n2. 第一顺序：配偶、子女、父母\n3. 有遗嘱的按遗嘱继承\n4. 建议办理继承公证"
        elif "房产" in prompt_lower:
            return "根据《民法典》物权编：\n1. 不动产物权需经登记生效\n2. 住宅用地使用权到期自动续期\n3. 租赁合同最长20年\n4. 建议核实产权登记信息"
        elif "消费者" in prompt_lower:
            return "根据《消费者权益保护法》：\n1. 欺诈行为三倍赔偿\n2. 质量问题可要求退货\n3. 7天无理由退货（特定商品除外）\n4. 可向12315投诉"
        else:
            if national_laws.get("success") and national_laws.get("list"):
                return f"关于「{prompt}」的问题，以上是相关法律条文。建议您：\n1. 仔细阅读法律原文\n2. 咨询专业律师获取具体意见\n3. 收集相关证据材料"
            else:
                return f"关于「{prompt}」的问题，建议您：\n1. 访问国家法律法规数据库查询\n2. 咨询专业律师\n3. 收集相关证据材料"
    
    def _fallback_response(self, prompt, national_laws, error_msg):
        """降级响应"""
        response = "**【提示】** AI服务暂时不可用，以下是法律知识库内容：\n\n"
        
        if national_laws.get("success") and national_laws.get("list"):
            for law in national_laws.get("list", [])[:2]:
                response += f"### 📚 {law.get('title', '法律条文')}\n\n"
                response += f"{law.get('content', '')}\n\n"
                if law.get('url'):
                    response += f"🔗 [查看原文]({law.get('url')})\n\n"
                response += "---\n\n"
        else:
            response += f"请访问国家法律法规数据库查询相关法律条文：\n"
            response += f"🔗 {self.national_law_db.get_recommended_link(prompt)}\n\n"
        
        response += "💡 您也可以稍后重试或咨询专业律师获取法律意见。"
        
        return response

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
    .law-card {
        background-color: #f8f9fa;
        border-left: 4px solid #2e7d32;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.title("⚖️ 司法流程辅助与节点提醒系统")
st.markdown("*连接国家法律法规数据库 | 智能法律咨询 | 支持演示模式*")

# 会话状态初始化
if "hy_client" not in st.session_state:
    st.session_state.hy_client = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = "法律解释"
if "use_demo" not in st.session_state:
    st.session_state.use_demo = True

# ===================== 侧边栏 =====================
with st.sidebar:
    st.markdown("## 📚 系统功能")
    
    st.markdown("---")
    
    # 腾讯云配置
    st.markdown("### 🔑 API配置")
    
    use_tencent = st.checkbox("启用腾讯云AI（需要密钥）", value=not st.session_state.use_demo)
    
    if use_tencent:
        secret_id = st.text_input("SecretId", type="password", placeholder="请输入腾讯云 SecretId")
        secret_key = st.text_input("SecretKey", type="password", placeholder="请输入腾讯云 SecretKey")
        
        if st.button("🔌 连接AI服务", use_container_width=True):
            if secret_id and secret_key:
                with st.spinner("正在连接..."):
                    try:
                        client = HunyuanClient(secret_id, secret_key, st.session_state.law_db)
                        if not client.use_demo:
                            st.session_state.hy_client = client
                            st.session_state.use_demo = False
                            st.success("✅ AI服务已连接")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ 连接失败，请检查密钥")
                    except Exception as e:
                        st.error(f"❌ 连接失败：{str(e)}")
            else:
                st.warning("请输入密钥")
    else:
        st.info("💡 使用演示模式（无需密钥）")
        if st.button("🔄 切换到演示模式", use_container_width=True):
            st.session_state.hy_client = HunyuanClient()
            st.session_state.use_demo = True
            st.rerun()
    
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
    
    # 模式选择
    st.markdown("### 🎯 对话模式")
    mode_options = {
        "法律解释": "📚 法律解释",
        "节点提醒": "⏰ 节点提醒", 
        "智能对话": "💬 智能对话",
    }
    
    for mode_key, mode_label in mode_options.items():
        if st.button(mode_label, key=f"mode_{mode_key}", use_container_width=True):
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
    
    # 系统状态
    st.markdown("### 📊 系统状态")
    if not st.session_state.use_demo and st.session_state.hy_client:
        st.success("✅ AI服务已连接")
    else:
        st.info("🔄 演示模式 - 使用本地法律库")
    
    st.markdown("---")
    
    # 使用帮助
    with st.expander("ℹ️ 使用帮助"):
        st.markdown("""
        **功能介绍：**
        - 📚 **法律解释**：解读法律条文，匹配相关法条
        - ⏰ **节点提醒**：分析案件流程节点，提醒法律时效
        - 💬 **智能对话**：日常法律咨询，通俗解释
        
        **数据来源：**
        - 🏛️ 国家法律法规数据库（全国人大官网）
        - 📖 内置法律知识库（涵盖民法典、劳动法、刑法等）
        
        **支持的法律领域：**
        - 婚姻家庭（离婚、结婚、抚养权）
        - 合同纠纷（违约、定金、赔偿）
        - 劳动纠纷（工资、加班、辞退）
        - 侵权责任（人身损害、财产损失）
        - 遗产继承
        - 房产纠纷
        - 消费者权益
        - 刑事法律
        
        **使用技巧：**
        - 支持多轮对话
        - 自动检索相关法律条文
        - 可直接输入具体问题
        - 按Enter键发送消息
        """)
    
    st.markdown("---")
    st.caption("司法流程辅助系统 v3.0")
    st.caption("数据来源：国家法律法规数据库")

# ===================== 初始化客户端 =====================
if st.session_state.hy_client is None:
    st.session_state.hy_client = HunyuanClient()
    st.session_state.use_demo = True

# ===================== 主聊天区域 =====================
# 显示欢迎消息
if not st.session_state.messages:
    welcome_msg = f"""您好！欢迎使用司法流程辅助系统。

**🏛️ 数据来源：国家法律法规数据库（全国人大官网）**
- 官网地址：https://flk.npc.gov.cn/
- 收录内容：宪法、法律、行政法规、司法解释等

**📖 内置法律知识库：**
- 民法典（婚姻、合同、侵权、继承、物权）
- 劳动合同法
- 刑法
- 消费者权益保护法

**⚡ 功能特点：**
- 自动检索相关法律条文
- 提供权威法律条文引用
- 支持多轮对话记忆
- 三种专业咨询模式

**💡 当前状态：** {"已连接腾讯云AI" if not st.session_state.use_demo else "演示模式（无需密钥）"}

**📝 您可以这样提问：**
- "离婚需要什么条件？"
- "公司拖欠工资怎么办？"
- "合同违约如何赔偿？"
- "被侵权了怎么索赔？"

请问有什么可以帮您的吗？"""
    
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

# 显示对话历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入框
prompt = st.chat_input("请输入您的法律问题，系统将自动检索相关法律条文...")
if prompt:
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 系统提示词
    system_prompts = {
        "法律解释": "你是专业的法律科普助手，请基于国家法律法规，通俗易懂地解读法律内容，提供准确的法律条文引用。",
        "节点提醒": "你是专业的法律流程助手，请分析案件的关键节点、法律时效、诉讼流程，给出清晰的提醒和建议。",
        "智能对话": "你是专业的法律顾问，请基于法律法规，用通俗易懂的语言解答用户的法律问题。"
    }
    
    system_prompt = system_prompts.get(st.session_state.mode, system_prompts["智能对话"])
    
    # 获取回复
    with st.chat_message("assistant"):
        with st.spinner("🔍 正在检索法律知识库..."):
            try:
                history = st.session_state.messages[:-1]
                response = st.session_state.hy_client.chat_with_history(history, system_prompt)
                
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
    "⚖️ 司法流程辅助系统 | 数据来源：国家法律法规数据库 | 提供权威法律咨询<br>"
    "⚠️ 本系统仅供参考，具体法律问题请咨询专业律师"
    "</div>",
    unsafe_allow_html=True
)
