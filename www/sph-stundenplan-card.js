class SphStundenplanCard extends HTMLElement {
  setConfig(config){this.config=config;}
  set hass(hass){
    const s=hass.states[this.config.entity]; if(!s)return;
    const days=s.attributes.tage||[], names=["Montag","Dienstag","Mittwoch","Donnerstag","Freitag"];
    this.innerHTML=`<ha-card header="${this.config.title||"Stundenplan"}"><div class="content">${days.slice(0,5).map((d,i)=>`<section><h3>${names[i]}</h3>${d.length?d.map(x=>`<div class="lesson"><span class="time">${x.start}–${x.end}</span><span><b>${x.subject||"Unterricht"}</b><small>${x.teacher||""}${x.room?" · "+x.room:""}</small></span></div>`).join(""):`<span class="empty">Kein Unterricht</span>`}</section>`).join("")}</div></ha-card>`;
    if(!this._styled){const st=document.createElement("style");st.textContent=`.content{padding:12px}section{margin-bottom:16px}h3{margin:0 0 8px}.lesson{display:flex;gap:12px;padding:7px 0;border-bottom:1px solid var(--divider-color)}.time{min-width:92px;color:var(--secondary-text-color)}small{display:block;color:var(--secondary-text-color);margin-top:2px}.empty{color:var(--secondary-text-color)}`;this.appendChild(st);this._styled=true;}
  }
  getCardSize(){return 6;}
}
customElements.define("sph-stundenplan-card",SphStundenplanCard);
window.customCards=window.customCards||[];
window.customCards.push({type:"sph-stundenplan-card",name:"SPH Stundenplan",description:"Stundenplan aus dem Schulportal Hessen"});
