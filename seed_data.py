"""
种子数据：预设少量典型题目用于初始测试
"""
import sys
sys.path.insert(0, ".")

from data.db.queries import insert_question
from pipeline.classifier import get_category_id

SEED = [
    ("Please explain what is hot carrier injection (HCI) effect in short channel MOSFET.",
     "short_answer", "器件设计",
     "HCI是短沟道MOSFET中载流子在高电场下获得足够能量注入栅氧化层的现象。导致Vth漂移、跨导退化、漏极电流下降。NMOS比PMOS更严重。缓解措施：LDD结构、降低工作电压、优化氧化层质量。",
     4, "HCI,热载流子注入,短沟道效应,可靠性"),
    ("Calculate Vth of n-MOSFET: Na=1e17 cm^-3, tox=10nm, Qox=5e10 cm^-2, phi_ms=-0.9V.",
     "calculation", "器件设计",
     "phi_F = 0.0259*ln(1e17/1.5e10) = 0.409V\nCox = 3.9*8.85e-14/(10e-7) = 3.45e-7 F/cm2\nVth = -0.9 + 2*0.409 + 1.84e-7/3.45e-7 - 5e10*1.6e-19/3.45e-7 = 0.428V",
     4, "阈值电压,tox,掺杂浓度,MOSFET"),
    ("请描述功率MOSFET中JFET效应的物理机制及其对导通电阻的影响。",
     "short_answer", "器件设计",
     "P-body之间的N-epi形成寄生JFET。漏压增大时耗尽层扩展使电流通道变窄，Ron增大。缓解：增大P-body间距、优化掺杂、采用SGT结构消除寄生JFET。",
     3, "JFET效应,导通电阻,功率MOSFET,VDMOS"),
    ("Compare SiC MOSFET and Si IGBT in power applications. Write in English.",
     "short_answer", "器件设计",
     "SiC MOSFET: Wide bandgap(3.26eV), higher breakdown field, lower Ron, faster switching, higher temp(300C+), no tail current. But higher cost, lower channel mobility, gate oxide reliability concerns.\nSi IGBT: Mature, lower cost, high current density(conductivity modulation), good ruggedness. But tail current, higher switching losses, limited to ~150C.",
     4, "SiC,MOSFET,IGBT,WBG,宽禁带,碳化硅"),
    ("画一个VDMOS的截面结构图，标注source/gate/drain/P-body/N-epi/N+衬底等区域。",
     "drawing", "器件设计",
     "从上到下：Source(N+)位于上表面两侧→P-body形成沟道→Gate(多晶硅)位于栅氧之上→N-epi漂移区承受耐压→N+衬底降低电阻→Drain底部金属。P-body之间形成寄生JFET。",
     3, "VDMOS,截面结构,功率器件"),
    ("Explain the physical mechanism of NBTI in PMOS devices. Major factors?",
     "short_answer", "可靠性分析",
     "NBTI(Negative Bias Temperature Instability): PMOS在负栅压+高温下Si-H键断裂，H向栅极扩散，留下界面态Dit和氧化层陷阱电荷。导致Vth绝对值增大、跨导退化。影响因素：温度(Arrhenius, Ea~0.1-0.15eV)、栅压(幂律)、时间(Δt^n)、栅氧厚度、氮含量、氢环境。",
     4, "NBTI,PMOS,界面态,可靠性退化"),
    ("What is latch-up effect in CMOS? Prevention methods?",
     "short_answer", "可靠性分析",
     "Latch-up是CMOS中寄生PNPN(SCR)触发导通引起的大电流现象。触发：过压瞬态、I/O过冲、辐射。防护：保护环(Guard Ring)、增加阱接触密度、增大NMOS/PMOS间距、SOI衬底、合理布局、ESD保护。",
     3, "Latch-up,闩锁,CMOS,SCR,ESD"),
    ("解释UIS测试的目的、原理及UIS失效的主要机制。",
     "short_answer", "可靠性分析",
     "UIS(Unclamped Inductive Switching)评估MOSFET在感性负载关断时的雪崩耐量。原理：MOSFET关断→电感电流不能突变→漏压升至击穿电压→雪崩耗散能量。失效机制：寄生BJT导通(Snapback)、热致失效(局部温度>400C)、电流不均匀分布、氧化层陷阱。改善：优化P-body、降低基区电阻。",
     4, "UIS,雪崩耐量,寄生BJT,Snapback,功率MOSFET"),
    ("描述BCD工艺的基本概念及典型工艺流程中的关键模块。",
     "short_answer", "半导体工艺",
     "BCD=Bipolar+CMOS+DMOS集成在同一芯片的工艺，主要用于功率管理IC。关键模块：埋层(隔离/降电阻)→外延层→深N阱(HV隔离)→高压P-Well→CMOS Well→Field Oxide/STI→栅氧(CMOS薄/HV厚)→多晶硅栅→LDD/Spacer→P-body+N+Source→接触孔/金属化。应用于电源管理、电机驱动、LED驱动、DC-DC等。",
     3, "BCD工艺,Bipolar,CMOS,DMOS,功率管理IC"),
    ("Explain the difference between LOCOS and STI. Which is preferred in advanced CMOS?",
     "short_answer", "半导体工艺",
     "LOCOS: 热氧化生长场氧，Si3N4掩膜，有鸟嘴效应侵占有源区面积。工艺简单但隔离间距大(~0.5um)。STI: 干法刻蚀槽+CVD填氧化层+CMP平坦化，无鸟嘴效应，隔离间距小(<0.1um)，平面性好。先进CMOS首选STI，因面积利用率高、适合亚0.25um节点。",
     3, "LOCOS,STI,鸟嘴效应,CMOS工艺,隔离"),
    ("Draw basic synchronous BUCK topology. Purpose of dead time?",
     "short_answer", "电路分析",
     "同步BUCK：输入电容→高侧MOSFET(HS主开关)→电感L→输出电容→低侧MOSFET(LS同步整流)。死区时间：HS和LS同时关断，防止直通(Shoot-through)导致VIN对GND短路。代价：体二极管导通(VF~0.7V)、反向恢复损耗。优化：自适应死区控制。",
     3, "BUCK,同步整流,死区时间,DC-DC,开关电源"),
    ("BUCK: Vin=12V, Vo=5V, L=10uH, C=100uF, Fsw=500kHz. Calculate D, delta_IL, delta_Vo(ESR=0).",
     "calculation", "电路分析",
     "D=Vo/Vin=5/12=0.417, delta_IL=(12-5)*0.417/(10uH*500kHz)=0.584A, delta_Vo=0.584/(8*100uF*500kHz)=1.46mV。实际纹波需考虑ESR影响，通常远大于容性纹波。",
     4, "BUCK,占空比,电流纹波,电压纹波,DC-DC"),
    ("解释带隙基准源(Bandgap Reference)的基本原理。为什么能提供零温度系数电压？",
     "short_answer", "电路分析",
     "Vref=VBE+K*delta_VBE。VBE负温度系数(-2mV/C)，delta_VBE=VT*ln(N)正温度系数(+0.087mV/C per unit)。选择合适K(~23)使正负抵消，Vref≈1.25V。实现：运放+BJT+电阻网络。应用：ADC/DAC参考、LDO参考、电源管理IC。",
     3, "带隙基准,Bandgap,PTAT,CTAT,温度系数,参考电压"),
    ("请列出功率MOSFET导通电阻Ron的主要组成部分。",
     "short_answer", "器件设计",
     "Ron = Rs(源极接触+金属电阻) + Rch(沟道电阻) + Ra(积累层电阻) + Rj(JFET区电阻) + Repi(漂移区电阻) + Rsub(衬底电阻) + Rd(漏极接触电阻)。高压器件中Repi主导(50-70%)，低压器件中Rch主导。降低Ron方法：提高掺杂、缩短沟道、优化JFET区、采用SGT等。",
     3, "导通电阻,Ron,功率MOSFET,漂移区,沟道电阻"),
    ("什么是RESURF原理？在LDMOS设计中如何应用RESURF技术提高击穿电压？",
     "short_answer", "器件设计",
     "RESURF(REduced SURface Field)原理：通过在N-epi下方引入P型掺杂层(P-substrate或P-buried layer)，使耗尽层在横向和纵向同时扩展，降低表面峰值电场。当N-epi掺杂剂量(Nepi*tepj)约为1e12 cm^-2时，击穿从表面转移到体区。优点：在相同外延条件下实现更高BV(可达传统结构的2-3倍)、降低比导通电阻Ron,sp。Double RESURF加入顶部P-top层进一步优化。",
     4, "RESURF,LDMOS,击穿电压,降低表面电场,功率器件"),
]

inserted = 0
for q_text, q_type, cat_name, answer, diff, kws in SEED:
    cat_id = get_category_id(cat_name)
    qid = insert_question(
        question_type=q_type,
        question_text=q_text,
        category_id=cat_id,
        answer_text=answer,
        difficulty=diff,
        keywords=kws,
        is_ai_generated=0,
        source_file="seed_data",
    )
    if qid:
        inserted += 1

print(f"种子数据插入完成: {inserted}/{len(SEED)} 道题")