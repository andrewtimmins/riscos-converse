#!/usr/bin/env python3
import base64, os
D=os.path.dirname(__file__)
def b64(f): return base64.b64encode(open(os.path.join(D,f),"rb").read()).decode()

SECTIONS=[
 ("Arrival","What a caller meets first",[
   ("login","Connect / Login","drop-shadowed wordmark, network strip, log-on bar"),
   ("newuser","New User Registration","styled application intro before the questionnaire"),
 ]),
 ("The hub","One consistent frame for everything",[
   ("mainmenu","Main Menu","icons, hot-keys, user & line banner, command prompt"),
 ]),
 ("Messages & files","The core of any board",[
   ("msgmenu","Message Bases","read / scan / inbox on the left, compose & send on the right"),
   ("filemenu","File Libraries","browse vs transfer, with protocol + batch queue"),
 ]),
 ("Play & community","The bit that makes a board feel alive",[
   ("doorsmenu","Doors & Games","the seven bundled games with star ratings"),
   ("bulletins","Bulletins & News","dated sysop announcements shown at log-on"),
   ("lastcallers","Last Callers","who called, from where, and what they did"),
   ("oneliners","The Wall","graffiti one-liners callers leave behind"),
 ]),
 ("You & the system","Self-serve and a bit of showing off",[
   ("settings","User Settings","ON/OFF toggles for ANSI, width, page-pause, editor"),
   ("stats","Hall of Fame","top posters & uploaders, door high scores, system totals"),
   ("voting","Voting Booth","live bar-chart poll results"),
   ("feedback","Feedback to Sysop","a private line to the operator"),
   ("help","Help & Commands","the hot-key reference, grouped by context"),
 ]),
 ("Exit","A proper send-off",[
   ("goodbye","Goodbye","call summary, 73!, and a NO CARRIER sign-off"),
 ]),
]

def figs():
    out=[]
    for title,sub,items in SECTIONS:
        out.append(f'<section><h2>{title}<span>{sub}</span></h2><div class="stack">')
        for f,cap,desc in items:
            out.append(f'''<figure>
      <figcaption class="cap"><span class="dot"></span><b>{cap}</b><span>{desc}</span></figcaption>
      <div class="crt"><img alt="{cap}" src="data:image/png;base64,{b64(f+'.png')}"></div>
    </figure>''')
        out.append('</div></section>')
    return "\n".join(out)

HTML=f"""<style>
  :root{{
    --ground:#0a0b0f; --panel:#111318; --panel2:#0d0f14;
    --cyan:#38d6d6; --amber:#ffb445; --green:#67e08a;
    --ink:#cdd4da; --mute:#727d88; --line:rgba(56,214,214,.18);
    --mono:ui-monospace,"SF Mono","Cascadia Code","JetBrains Mono",Menlo,Consolas,monospace;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:
      radial-gradient(120% 70% at 50% -8%,rgba(56,214,214,.06),transparent 60%),var(--ground);
    color:var(--ink);font-family:var(--mono);line-height:1.55;-webkit-font-smoothing:antialiased;
    padding:48px 20px 72px;}}
  .wrap{{max-width:1180px;margin:0 auto;}}
  .eyebrow{{font-size:12px;letter-spacing:.32em;text-transform:uppercase;color:var(--cyan);
    margin:0 0 12px;display:flex;align-items:center;gap:10px;}}
  .eyebrow::before{{content:"";width:26px;height:1px;background:var(--cyan);opacity:.6;}}
  h1{{font-size:clamp(30px,5vw,50px);margin:0 0 6px;font-weight:700;color:#fff;text-wrap:balance;}}
  h1 b{{color:var(--amber);}}
  .lede{{color:var(--mute);max-width:74ch;margin:0 0 14px;font-size:15px;}}
  .lede code{{color:var(--cyan);background:rgba(56,214,214,.08);padding:1px 6px;border-radius:3px;}}
  .meta{{display:flex;gap:26px;flex-wrap:wrap;color:var(--mute);font-size:12px;margin:0 0 44px;
    padding-top:14px;border-top:1px solid var(--line);}}
  .meta b{{color:var(--ink);font-weight:600;}}
  section{{margin-bottom:46px;}}
  h2{{font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:var(--amber);
    margin:0 0 18px;display:flex;align-items:baseline;gap:14px;
    border-bottom:1px solid var(--line);padding-bottom:10px;}}
  h2 span{{color:var(--mute);font-size:12px;letter-spacing:.02em;text-transform:none;}}
  .stack{{display:flex;flex-direction:column;gap:26px;}}
  figure{{margin:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel2);
    box-shadow:0 22px 54px -32px rgba(0,0,0,.9),inset 0 0 90px -42px rgba(56,214,214,.10);}}
  .cap{{display:flex;align-items:baseline;gap:13px;padding:12px 18px;border-bottom:1px solid var(--line);
    background:linear-gradient(180deg,rgba(56,214,214,.05),transparent);}}
  .cap b{{color:#fff;font-size:13.5px;letter-spacing:.03em;}} .cap span{{color:var(--mute);font-size:12px;}}
  .cap .dot{{width:9px;height:9px;border-radius:50%;background:var(--amber);box-shadow:0 0 10px var(--amber);
    flex:0 0 auto;align-self:center;}}
  .crt{{position:relative;overflow-x:auto;background:#000;}}
  .crt img{{display:block;width:100%;min-width:720px;image-rendering:pixelated;}}
  .crt::after{{content:"";position:absolute;inset:0;pointer-events:none;
    background:repeating-linear-gradient(180deg,rgba(0,0,0,0) 0 2px,rgba(0,0,0,.15) 2px 3px);mix-blend-mode:multiply;}}
  .plan{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin-top:10px;}}
  .card{{border:1px solid var(--line);border-radius:10px;padding:20px 22px;background:var(--panel);}}
  .card h3{{margin:0 0 14px;font-size:12px;letter-spacing:.2em;text-transform:uppercase;}}
  .card.done h3{{color:var(--green);}} .card.next h3{{color:var(--cyan);}} .card.watch h3{{color:var(--amber);}}
  ul{{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:9px;}}
  li{{font-size:13.5px;padding-left:20px;position:relative;}}
  li::before{{position:absolute;left:0;top:0;}}
  .done li::before{{content:"\\2713";color:var(--green);}}
  .next li::before{{content:"\\25B8";color:var(--cyan);}}
  .watch li::before{{content:"!";color:var(--amber);font-weight:700;left:3px;}}
  li small{{display:block;color:var(--mute);font-size:12px;margin-top:1px;}}
  footer{{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);color:var(--mute);
    font-size:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;}}
  footer b{{color:var(--cyan);font-weight:400;}}
</style>

<div class="wrap">
  <p class="eyebrow">Demo BBS &middot; ANSI redesign &middot; the full journey</p>
  <h1>The <b>Yellow&nbsp;Toaster</b>, end to end</h1>
  <p class="lede">Sixteen CP437 screens covering the whole caller journey &mdash; arrival, the hub,
  messages &amp; files, the community corner, self-serve tools, and a proper send-off. Every screen is rendered
  with the BBS's real terminal font (<code>Font,ffd</code>) and 16-colour palette, then emitted
  as an <code>.ANS</code> file the <code>type</code> command displays. Structure follows the
  classic WWIV/Renegade &rarr; Mystic playbook: last callers, bulletins and one-liners are the
  bits that make a board feel lived-in.</p>
  <div class="meta">
    <span><b>16</b> screens</span><span><b>80&times;25</b> CP437</span>
    <span><b>16</b> ANSI colours</span><span>one shared frame system</span>
    <span>deployed &amp; wired &mdash; all via <b>type</b></span>
  </div>

  {figs()}

  <section>
    <h2>Where this goes<span>the build from here</span></h2>
    <div class="plan">
      <div class="card done"><h3>Done</h3><ul>
        <li>All 16 screens built &amp; deployed<small>into <code>!Converse/BBS/Screens</code></small></li>
        <li>Every script wired<small>menus <code>type</code> their screen &amp; dispatch hot-keys</small></li>
        <li>Login sequence added<small>bulletins &rarr; last callers &rarr; new-scan &rarr; menu</small></li>
        <li>All references verified<small>screens, sub-scripts &amp; door paths resolve</small></li>
      </ul></div>
      <div class="card next"><h3>Next</h3><ul>
        <li>Boot &amp; walk the whole journey on the emulator</li>
        <li>Tune door-launch type/line-passing from what we see</li>
        <li>Seed sample content behind the menus</li>
      </ul></div>
      <div class="card watch"><h3>Still true</h3><ul>
        <li>Live boot confirms the real render<small>&amp; the door-launch type/line-passing</small></li>
        <li>Bases are empty<small>seeding sample messages/files/callers is the last mile</small></li>
      </ul></div>
    </div>
  </section>

  <footer>
    <span>Rendered from <b>!Converse/Resources/Font,ffd</b> &middot; CP437 &middot; 16 colours</span>
    <span>The Yellow Toaster &middot; a Converse BBS</span>
  </footer>
</div>
"""
open(os.path.join(D,"preview.html"),"w").write(HTML)
print("wrote preview.html",len(HTML),"bytes")
