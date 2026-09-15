const OC={
  setActive(){
    const path=location.pathname;
    document.querySelectorAll(".nav a").forEach(a=>{
      const href=a.getAttribute("href");
      a.classList.toggle("active", href===path || (path==="/" && href==="/dashboard"));
    });
  },
  fileSize(bytes){return bytes<1024*1024?(bytes/1024).toFixed(1)+" KB":(bytes/1024/1024).toFixed(1)+" MB"},
  saveReport(report,file){
    const reports=JSON.parse(localStorage.getItem("oc_reports")||"[]");
    reports.unshift({
      id:Date.now(),name:file.name,date:new Date().toISOString(),
      words:report.document.words,originality:report.originality,
      similarity:report.highest_similarity,ai:report.ai_writing.indicator_score,
      matches:report.matches||[],citation:report.citation_health
    });
    localStorage.setItem("oc_reports",JSON.stringify(reports.slice(0,30)));
  },
  reports(){return JSON.parse(localStorage.getItem("oc_reports")||"[]")},
  escape(s){return String(s).replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]))}
};
document.addEventListener("DOMContentLoaded",()=>OC.setActive());
