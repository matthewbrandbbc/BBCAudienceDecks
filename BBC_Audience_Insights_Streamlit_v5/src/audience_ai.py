from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
import re
from typing import Iterable

from .chatbot_knowledge import DEFINITIONS, GWI_CORE_URL, GWI_METHOD_URL, GWI_WEIGHTING_URL, PURPOSE, SLIDE_GUIDE, index_definition
from .config import MIN_RESPONSES, PLATFORM_COLUMNS
from .data_engine import WorkbookRepository, clean_audience_name, format_compact

START = {"Cross Platform": 40, "Digital": 46, "TV": 63}
END = {"Cross Platform": 45, "Digital": 62, "TV": 68}
LABELS = {
  69:"business",70:"economy, finance, entrepreneurship and investments",71:"exploring the world",72:"international travel",73:"following the latest technology trends and news",74:"early adoption of new technology",75:"interest in other cultures and countries",76:"theatre, film and cinema",77:"following three or more sports",78:"playing or watching sport",79:"personal healthcare",80:"health food, drinks and nutrition",
  81:"browsing social media most days",82:"watching short-form video most days",83:"watching online video and how-to content most days",84:"reading online press and articles most days",85:"watching broadcast TV most days",86:"watching streaming services most days",87:"listening to podcasts most days",
  88:"men",89:"women",90:"university graduates",91:"Gen Z",92:"Millennials",93:"Gen X",94:"Baby Boomers and the Silent Generation",95:"parents",96:"high-income consumers",97:"international travellers",
  98:"people working in smaller organisations",99:"people working in larger organisations",100:"business decision-makers",101:"finance business decision-makers",102:"IT business decision-makers",103:"senior management",104:"C-Suites",105:"company strategy decision-makers",106:"recruitment decision-makers",107:"sustainability and energy decision-makers",
  108:"believing AI benefits society",109:"believing AI enhances daily life",110:"believing AI can help solve major global problems",111:"believing AI will create more job opportunities",
  112:"discovering brands through social-media ads",113:"discovering brands through TV ads",114:"discovering brands through website ads",115:"discovering brands through CTV or streaming-video ads",116:"discovering brands through email or newsletters",117:"discovering brands through podcast ads",118:"discovering brands through news articles",
  119:"being first to try new things",120:"buying brands seen advertised",121:"buying premium versions of products",
}
CATEGORIES = {
  "BBC.com pillar alignment":range(69,81), "platform and media consumption":range(81,88),
  "audience demographics":range(88,98), "employment profile":range(98,108),
  "AI attitudes":range(108,112), "brand discovery":range(112,119), "discovery attitudes":range(119,122),
}
SLIDES = {"BBC.com pillar alignment":4,"audience demographics":5,"employment profile":6,"platform and media consumption":7,"brand discovery":8,"discovery attitudes":9,"AI attitudes":10}
ALIASES = {
  69:("business interest",),70:("finance interest","economy","investments"),71:("explore the world",),72:("international travel",),73:("technology trends","tech trends"),74:("early adopter","new technology"),75:("other cultures",),76:("theatre","cinema"),77:("follow sports",),78:("playing sport","watching sport"),79:("healthcare",),80:("health food","nutrition"),
  81:("social media",),82:("short video","short form video","tiktok"),83:("online video","how to video"),84:("online press","online articles"),85:("broadcast tv",),86:("streaming",),87:("podcast",),
  88:("male","men"),89:("female","women"),90:("graduates","degree"),91:("gen z",),92:("millennials",),93:("gen x",),94:("baby boomers","silent generation"),95:("parents","children"),96:("high income","affluent"),97:("international travellers","international travelers"),
  98:("small organisations","small organizations","smes"),99:("large organisations","large organizations"),100:("business decision makers","bdms"),101:("finance decision makers","fbdms"),102:("it decision makers","itbdms"),103:("senior management",),104:("c suites","c suite","executives"),105:("company strategy",),106:("recruitment","hiring"),107:("sustainability decision makers",),
  108:("ai benefits society",),109:("ai enhances daily life",),110:("ai solve global problems",),111:("ai job opportunities","ai create jobs"),112:("social media ads",),113:("tv ads",),114:("website ads",),115:("ctv ads","streaming video ads"),116:("email","newsletters"),117:("podcast ads",),118:("news articles",),119:("first to try new things",),120:("brands seen advertised",),121:("premium version","premium products"),
}
DEFINITION_ROWS={"Business Decision Makers (BDMs)":{100},"C-Suites":{104},"FBDMs – Finance Business Decision Makers":{101},"Gen Z":{91},"IT Business Decision Makers (ITBDMs)":{102},"Sports Enthusiasts":{78}}
AUDIENCES={"all audiences":"All Audiences","total bbc audience":"All Audiences","c suite":"C-Suites","c suites":"C-Suites","hnwi":"HNWIs","hnwis":"HNWIs","sme":"SMEs","smes":"SMEs","bdm":"Business Decision Makers (BDMs)","bdms":"Business Decision Makers (BDMs)","fbdm":"FBDMs – Finance Business Decision Makers","fbdms":"FBDMs – Finance Business Decision Makers","itbdm":"IT Business Decision Makers (ITBDMs)","itbdms":"IT Business Decision Makers (ITBDMs)"}
REGIONS={"global":"All Markets","worldwide":"All Markets","all markets":"All Markets","north america":"North America","latin america":"Latin America","latam":"Latin America","europe":"Europe","middle east":"Middle East","africa":"Africa","south asia":"South Asia","apac":"APAC","asia pacific":"APAC"}
PLATFORMS={"cross platform":"Cross Platform","cross-platform":"Cross Platform","digital":"Digital","online":"Digital","tv":"TV","television":"TV"}

@dataclass(frozen=True)
class Evidence:
    statement:str; value:str; source_label:str; cells:str=""; slide:int|None=None; scope:str=""; reason:str=""

@dataclass(frozen=True)
class Affinity:
    label:str; index:float; percent:float; category:str; row:int; source_label:str; cells:str; responses:int

@dataclass(frozen=True)
class AudienceOverview:
    headline:str; bullets:tuple[str,...]; interpretation_note:str; evidence:tuple[Evidence,...]
    @property
    def sales_takeout(self): return self.interpretation_note

@dataclass(frozen=True)
class GroundedAnswer:
    answer:str; evidence:tuple[Evidence,...]=(); resolved_scope:str=""; relevant_slide:int|None=None; intent:str=""

def norm(value): return re.sub(r"[^a-z0-9]+"," ",str(value).casefold()).strip()
def pct(value): return f"{round(float(value)*100):.0f}%"
def platform_phrase(value): return {"Cross Platform":"cross-platform","Digital":"digital","TV":"TV"}[value]
def scope(audience,region,platform): return f"{audience} · {region} · {platform}"
def phrase(audience): return "the Total BBC Audience" if audience=="All Audiences" else f"BBC {clean_audience_name(audience)}"
def index_phrase(value,comparison):
    diff=round(value-100)
    return f"{diff}% more likely than {comparison}" if diff>0 else (f"{abs(diff)}% less likely than {comparison}" if diff<0 else f"in line with {comparison}")

class GroundedAudienceEngine:
    """Deterministic retrieval-and-response layer; no LLM or API is called."""
    def __init__(self,repo:WorkbookRepository):
        self.repo=repo; self.audiences=tuple(repo.audience_map("All Markets")); self.regions=tuple(repo.paths)
    def comparison_label(self,audience,region):
        return f"the average online adult in {region}" if audience=="All Audiences" else f"the equivalent {clean_audience_name(audience)} audience in {region}"
    def reach_evidence(self,region,audience,platform):
        ws=self.repo.sheet(region,audience); cols=PLATFORM_COLUMNS[platform]; response=f"{cols['responses']}16"; n=int(ws[response].value or 0)
        if n<MIN_RESPONSES:return None
        u,r=f"{cols['universe']}16",f"{cols['row_percent']}16"
        return Evidence(f"BBC {platform_phrase(platform)} monthly reach",f"{format_compact(ws[u].value)} ({pct(ws[r].value)} of the selected audience); Responses {n}",f"GWI {region} — {audience}",f"{u}, {r}, {response}",2,scope(audience,region,platform),"Selected reach measure")
    def competitive_evidence(self,region,audience,platform):
        items=self.repo.supported_competitor_set(region,audience,START[platform],END[platform])
        if not items or not any(x.name.casefold()=="bbc" for x in items):return None
        rank=next(i for i,x in enumerate(items,1) if x.name.casefold()=="bbc"); bbc=next(x for x in items if x.name.casefold()=="bbc")
        detail=f"1st of {len(items)}, reaching {format_compact(bbc.value)}" if rank==1 else f"ranked {rank} of {len(items)}, reaching {format_compact(bbc.value)}; {items[0].name} has the highest reported reach at {format_compact(items[0].value)}"
        return Evidence(f"BBC competitive position on {platform_phrase(platform)}",detail,f"GWI {region} — {audience}",f"C{START[platform]}:E{END[platform]}",3,scope(audience,region,platform),"Available competitive set")
    def affinities(self,region,audience,platform,rows:Iterable[int]=range(69,122)):
        ws=self.repo.sheet(region,audience); cols=PLATFORM_COLUMNS[platform]; out=[]
        for row in rows:
            if row not in LABELS:continue
            n=int(ws[f"{cols['responses']}{row}"].value or 0)
            if n<MIN_RESPONSES:continue
            category=next((k for k,v in CATEGORIES.items() if row in v),"audience profile")
            out.append(Affinity(LABELS[row],float(ws[f"{cols['index']}{row}"].value),float(ws[f"{cols['percent']}{row}"].value),category,row,f"GWI {region} — {audience}",f"{cols['percent']}{row}, {cols['index']}{row}, {cols['responses']}{row}",n))
        return sorted(out,key=lambda x:(-x.index,-x.percent,x.row))
    def ranked_affinities(self,region,audience,platform,rows,limit=5,exclude_definition=True):
        excluded=DEFINITION_ROWS.get(audience,set()) if exclude_definition else set()
        return [x for x in self.affinities(region,audience,platform,rows) if x.row not in excluded][:limit]
    def metric(self,region,audience,platform,row):
        items=self.affinities(region,audience,platform,[row]); return items[0] if items else None
    def _evidence(self,item,audience,region,platform,reason):
        return Evidence(item.label,f"Composition {pct(item.percent)}; Index {round(item.index)}; Responses {item.responses}",item.source_label,item.cells,SLIDES.get(item.category),scope(audience,region,platform),reason)
    def composition_evidence(self,region,audience,platform,row):
        item=self.metric(region,audience,platform,row)
        if not item:raise ValueError("Response base below reporting threshold")
        return self._evidence(item,audience,region,platform,"Requested composition measure")
    def top_distinctive_affinity(self,region,audience,platform):
        items=self.ranked_affinities(region,audience,platform,(*range(69,88),*range(108,122)),1); return items[0] if items else None
    def overview(self,region,audience,platform):
        reach=self.reach_evidence(region,audience,platform); comp=self.competitive_evidence(region,audience,platform); item=self.top_distinctive_affinity(region,audience,platform); bullets=[]; evidence=[]
        if reach:evidence.append(reach);bullets.append(f"BBC’s reported {platform_phrase(platform)} reach is {reach.value.split(';')[0]} in {region} (Slide 2).")
        if comp:evidence.append(comp);bullets.append(f"Within the available competitive set, BBC is {comp.value} (Slide 3).")
        if item:
            evidence.append(self._evidence(item,audience,region,platform,"Highest supported non-definitional index"));bullets.append(f"A notable reported characteristic is {item.label}: {pct(item.percent)} composition and Index {round(item.index)}, or {index_phrase(item.index,self.comparison_label(audience,region))} (Slide {SLIDES[item.category]}).")
        if not bullets:bullets=[f"No statistics are shown because the available response bases are below {MIN_RESPONSES}."]
        return AudienceOverview(f"{audience} in {region}",tuple(bullets),"Read reach, composition and index together. These survey results describe reported patterns and do not establish causes or predict campaign outcomes.",tuple(evidence))
    def _mentioned(self,q,aliases,candidates=()):
        terms=dict(aliases); normal=norm(q)
        for c in candidates:terms[norm(c)]=c;terms[norm(clean_audience_name(c))]=c
        found=[]
        for alias,value in sorted(terms.items(),key=lambda x:-len(x[0])):
            m=re.search(rf"\b{re.escape(norm(alias))}\b",normal)
            if m and value not in [x[1] for x in found]:found.append((m.start(),value))
        return [v for _,v in sorted(found)]
    def _resolve(self,q,region,audience,platform):
        r=self._mentioned(q,REGIONS);a=self._mentioned(q,AUDIENCES,self.audiences);p=self._mentioned(q,PLATFORMS)
        return (r[0] if r else region,a[0] if a else audience,p[0] if p else platform)
    def _metric_row(self,q):
        normal=norm(q)
        for row,aliases in ALIASES.items():
            if any(re.search(rf"\b{re.escape(norm(a))}\b",normal) for a in aliases):return row
        words=[x for x in normal.split() if len(x)>=5]; keys={w:r for r,a in ALIASES.items() for term in a for w in norm(term).split() if len(w)>=5}
        for word in words:
            match=get_close_matches(word,keys,n=1,cutoff=.82)
            if match:return keys[match[0]]
        return None
    def _definition(self,normal,region,audience,platform):
        s=scope(audience,region,platform)
        if "chatbot" in normal and any(x in normal for x in ("what","purpose","help")):return GroundedAnswer(PURPOSE,resolved_scope=s,intent="purpose")
        if ("index" in normal or "affinity" in normal) and any(x in normal for x in ("what","mean","explain","definition")):return GroundedAnswer(index_definition(self.comparison_label(audience,region)),resolved_scope=s,intent="definition")
        if "composition" in normal and any(x in normal for x in ("what","mean","explain","definition")):return GroundedAnswer(DEFINITIONS["composition"],resolved_scope=s,intent="definition")
        if "reach percentage" in normal or "reach percent" in normal:return GroundedAnswer(DEFINITIONS["reach_percent"],resolved_scope=s,relevant_slide=2,intent="definition")
        if normal in {"what is reach","define reach"} or ("reach" in normal and any(x in normal for x in ("mean","explain","definition"))):return GroundedAnswer(DEFINITIONS["reach"],resolved_scope=s,relevant_slide=2,intent="definition")
        if any(x in normal for x in ("responses","base size","sample size")) and any(x in normal for x in ("what","mean","explain","why")):return GroundedAnswer(DEFINITIONS["responses"],resolved_scope=s,intent="definition")
        if "universe" in normal and any(x in normal for x in ("what","mean","explain")):return GroundedAnswer(DEFINITIONS["universe"],resolved_scope=s,intent="definition")
        if any(x in normal for x in ("survey","gwi","methodology","weighting","quota")):
            if any(x in normal for x in ("weight","quota","representative")):text=DEFINITIONS["weighting"]+f"\n\nGWI methods: {GWI_WEIGHTING_URL}"
            elif any(x in normal for x in ("market","countr","where")):text=f"GWI Core currently operates across 53 markets. This BBC report uses {self.repo.markets_footer(region)}. Use the report scope when interpreting its figures.\n\nGWI Core: {GWI_CORE_URL}"
            else:text=DEFINITIONS["survey"]+f"\n\nGWI methodology: {GWI_METHOD_URL}"
            return GroundedAnswer(text,resolved_scope=s,intent="methodology")
        if any(x in normal for x in ("what is on slide","what does slide","slide guide","slides show")):
            m=re.search(r"slide\s*(\d+)",normal)
            if m and int(m.group(1)) in SLIDE_GUIDE:
                n=int(m.group(1)); title,desc=SLIDE_GUIDE[n];return GroundedAnswer(f"Slide {n} is **{title}**. {desc}",resolved_scope=s,relevant_slide=n,intent="slide guide")
            return GroundedAnswer("The report sections are:\n\n"+"\n".join(f"- Slide {n}: **{t}** — {d}" for n,(t,d) in SLIDE_GUIDE.items()),resolved_scope=s,intent="slide guide")
    def _category(self,normal):
        if "ai" in normal:return range(108,112),10,"AI attitudes"
        if "brand discover" in normal or "discover brands" in normal:return range(112,119),8,"brand discovery"
        if any(x in normal for x in ("discovery attitude","advertising attitude","premium")):return range(119,122),9,"discovery attitudes"
        if any(x in normal for x in ("media consumption","platform consumption","media habit")):return range(81,88),7,"platform and media consumption"
        if "pillar" in normal:return range(69,81),4,"BBC.com pillar alignment"
        if any(x in normal for x in ("employment","firmographic","business title","role responsib")):return range(98,108),6,"employment profile"
        if any(x in normal for x in ("demographic","age profile")):return range(88,98),5,"audience demographics"
    def _category_answer(self,rows,slide,label,region,audience,platform):
        items=self.ranked_affinities(region,audience,platform,rows,4)
        if not items:return GroundedAnswer(f"No {label} statistics are reportable because the relevant response bases are below {MIN_RESPONSES}.",resolved_scope=scope(audience,region,platform),relevant_slide=slide,intent="suppression")
        comparison=self.comparison_label(audience,region);lines=[f"- **{x.label}:** {pct(x.percent)} composition; Index {round(x.index)} ({index_phrase(x.index,comparison)})." for x in items]
        return GroundedAnswer(f"For **{phrase(audience)}**, the highest-indexing supported {label} statements are:\n\n"+"\n".join(lines)+f"\n\nSee Slide {slide}. These reported attitudes or behaviours do not establish their causes.",tuple(self._evidence(x,audience,region,platform,f"Highest supported {label} index") for x in items),scope(audience,region,platform),slide,"category")
    def _profile(self,region,audience,platform):
        if audience=="All Audiences":return GroundedAnswer("Please select or name a specialist BBC audience so I can describe its demographic and employment profile.",resolved_scope=scope(audience,region,platform),intent="clarification")
        # Always represent both profile slides: two demographic observations,
        # one employment observation, then two non-definition qualities.
        items=self.ranked_affinities(region,audience,platform,range(88,98),2)+self.ranked_affinities(region,audience,platform,range(98,108),1)+self.ranked_affinities(region,audience,platform,(*range(69,88),*range(108,122)),2)
        comparison=self.comparison_label(audience,region);lines=[f"- **{x.label}:** {pct(x.percent)} composition; Index {round(x.index)} ({index_phrase(x.index,comparison)}). See Slide {SLIDES[x.category]}." for x in items]
        return GroundedAnswer(f"This describes **{phrase(audience)}**, not everyone in the wider {clean_audience_name(audience)} group. Three supported demographic or employment observations, followed by two other notable qualities:\n\n"+"\n".join(lines)+"\n\nThese are survey associations, not explanations of cause. Specialist exports omit Slides 5 and 6, but the chatbot can still use their validated source rows.",tuple(self._evidence(x,audience,region,platform,"Selected profile observation") for x in items),scope(audience,region,platform),5,"profile")
    def _comparison(self,q,region,audience,platform,row):
        audiences=self._mentioned(q,AUDIENCES,self.audiences);regions=self._mentioned(q,REGIONS)
        pairs=[(region,audiences[0]),(region,audiences[1])] if len(audiences)>=2 else ([(regions[0],audience),(regions[1],audience)] if len(regions)>=2 else [])
        if not pairs:return None
        lines=[];evidence=[]
        for r,a in pairs:
            item=self.metric(r,a,platform,row) if row else None
            if row and item:lines.append(f"- **{a} in {r}:** {pct(item.percent)} composition; Index {round(item.index)} versus {self.comparison_label(a,r)}.");evidence.append(self._evidence(item,a,r,platform,"Requested like-for-like comparison"))
            elif row:lines.append(f"- **{a} in {r}:** not reportable because Responses is below {MIN_RESPONSES}.")
            else:
                reach=self.reach_evidence(r,a,platform)
                if reach:lines.append(f"- **{a} in {r}:** reach {reach.value.split(';')[0]}.");evidence.append(reach)
                else:lines.append(f"- **{a} in {r}:** reach is not reportable because Responses is below {MIN_RESPONSES}.")
        return GroundedAnswer("A like-for-like comparison using the same platform and reporting period:\n\n"+"\n".join(lines)+"\n\nThis describes differences in the reported data; it does not explain what caused them.",tuple(evidence),scope(audience,region,platform),evidence[0].slide if evidence else None,"comparison")
    def answer(self,question,region,audience,platform,previous_question=None,previous_scope=None):
        if not question.strip():return GroundedAnswer("Ask a question about a slide, reach, composition, index, methodology or an audience profile.")
        normal=norm(question);follow=bool(re.match(r"^(what|how) about\b|^and\b|^compare with\b|^same for\b",normal))
        if previous_scope and follow:audience,region,platform=previous_scope
        region,audience,platform=self._resolve(question,region,audience,platform);intent=f"{previous_question} {question}" if previous_question and follow else question;normal=norm(intent);s=scope(audience,region,platform)
        defined=self._definition(normal,region,audience,platform)
        if defined:return defined
        row=self._metric_row(intent)
        mentioned_audiences=self._mentioned(question,AUDIENCES,self.audiences)
        if row is not None and any(row in DEFINITION_ROWS.get(name,set()) for name in mentioned_audiences):
            # Audience names such as C-Suites are scope, not a requested metric,
            # unless the question explicitly asks for their composition/index.
            if not any(x in normal for x in ("composition of","index for","percentage of","percent of")):
                row=None
        if any(x in normal for x in ("compare","versus"," vs ","difference between")):
            answer=self._comparison(question,region,audience,platform,row)
            return answer or GroundedAnswer("Please name the two audiences or two regions you want to compare. I will keep the platform and reporting period the same.",resolved_scope=s,intent="clarification")
        if re.search(r"what (?:do|does|are) (?:bbc )?.+ (?:look like|profile)",normal) or any(x in normal for x in ("audience profile","describe this audience")):return self._profile(region,audience,platform)
        category=self._category(normal)
        if category and any(x in normal for x in ("what","think","attitude","habit","discover","profile","show","tell")):return self._category_answer(*category,region,audience,platform)
        if row is not None and any(x in normal for x in ("percentage","percent","proportion","share","composition","index","likely")):
            item=self.metric(region,audience,platform,row)
            if not item:return GroundedAnswer(f"That statistic is not reportable because Responses is below {MIN_RESPONSES}. Universe, composition and index are suppressed together.",resolved_scope=s,intent="suppression")
            slide=SLIDES[item.category];ev=self._evidence(item,audience,region,platform,"Requested metric")
            return GroundedAnswer(f"For {phrase(audience)} in {region}, **{pct(item.percent)}** report {item.label}. The Index is **{round(item.index)}**, meaning this is {index_phrase(item.index,self.comparison_label(audience,region))}. See Slide {slide}.",(ev,),s,slide,"metric")
        if any(x in normal for x in ("competitor","competitive","rank","cnn","cnbc","ft")):
            ev=self.competitive_evidence(region,audience,platform)
            if not ev:return GroundedAnswer(f"The competitive statistic is not reportable because the BBC response base is below {MIN_RESPONSES}.",resolved_scope=s,relevant_slide=3,intent="suppression")
            note=" The available competitive set does not contain the Financial Times, so a direct BBC-versus-FT comparison is not supported." if "ft" in normal else ""
            return GroundedAnswer(f"For {phrase(audience)} in {region}, {ev.statement.lower()} is {ev.value}.{note} See Slide 3.",(ev,),s,3,"competitive")
        if any(x in normal for x in ("reach","how many","audience size","scale")):
            ev=self.reach_evidence(region,audience,platform)
            if not ev:return GroundedAnswer(f"The reach statistic is not reportable because Responses is below {MIN_RESPONSES}. Universe, composition and index are suppressed together.",resolved_scope=s,relevant_slide=2,intent="suppression")
            return GroundedAnswer(f"BBC’s estimated {platform_phrase(platform)} monthly reach among {phrase(audience)} in {region} is {ev.value.split(';')[0]}. See Slide 2.",(ev,),s,2,"reach")
        if "which audience" in normal or "what audience" in normal:
            category=self._category(normal) or ((*range(69,88),*range(108,122)),4,"distinctive qualities");candidates=[]
            for a in self.audiences:
                if a=="All Audiences":continue
                vals=self.ranked_affinities(region,a,platform,category[0],1)
                if not vals:return GroundedAnswer("I can’t make a reliable number-one claim because at least one comparable audience does not have a reportable result. I can compare named audiences instead.",resolved_scope=s,relevant_slide=category[1],intent="ranking")
                candidates.append((vals[0],a))
            candidates.sort(key=lambda x:(-x[0].index,-x[0].percent,x[1]));item,winner=candidates[0];ties=[a for x,a in candidates if x.index==item.index]
            ev=self._evidence(item,winner,region,platform,"Complete-audience number-one comparison");word="joint-highest" if len(ties)>1 else "highest"
            return GroundedAnswer(f"Within the complete set of reportable audiences, **{winner}** has the {word} supported index for {item.label}: Index {round(item.index)}, composition {pct(item.percent)}. This is a ranking within this dataset, not a recommendation or explanation of cause. See Slide {category[1]}.",(ev,),s,category[1],"ranking")
        if any(x in normal for x in ("top index","highest index","top indexing","highest indexing","affinit","more likely","qualities","characteristics")):
            items=self.ranked_affinities(region,audience,platform,range(69,122),5)
            if not items:return GroundedAnswer(f"No reportable qualities were found because the relevant response bases are below {MIN_RESPONSES}.",resolved_scope=s,intent="suppression")
            comparison=self.comparison_label(audience,region);lines=[f"- **{x.label}:** Index {round(x.index)} ({index_phrase(x.index,comparison)}); composition {pct(x.percent)}. See Slide {SLIDES[x.category]}." for x in items]
            return GroundedAnswer(f"The highest-indexing supported qualities for {phrase(audience)} are:\n\n"+"\n".join(lines)+"\n\nDefinition traits are excluded where identifiable. The measures may overlap and should not be added together.",tuple(self._evidence(x,audience,region,platform,"Highest supported non-definitional index") for x in items),s,SLIDES[items[0].category],"affinity")
        return GroundedAnswer("Sorry, I can’t answer that right now. I can help explain the audience slides, definitions and GWI methodology, or compare supported figures from the available workbooks.",resolved_scope=s,intent="unsupported")
