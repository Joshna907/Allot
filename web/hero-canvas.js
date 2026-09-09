const VERTEX_SHADER = `
attribute vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }
`;

const FRAGMENT_SHADER = `
precision highp float;
uniform vec2 resolution;
uniform float time;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453123); }
float noise(vec2 p) {
  vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash(i),hash(i+vec2(1.0,0.0)),f.x),mix(hash(i+vec2(0.0,1.0)),hash(i+vec2(1.0,1.0)),f.x),f.y);
}
float fbm(vec2 p) {
  float v=0.0, a=0.52; mat2 turn=mat2(.80,.60,-.60,.80);
  for(int i=0;i<6;i++){v+=a*noise(p);p=turn*p*2.03+.17;a*=.5;} return v;
}
void main() {
  vec2 uv=gl_FragCoord.xy/resolution.xy;
  vec2 p=uv; p.x*=resolution.x/resolution.y;
  float t=time*.115; vec2 drift=vec2(t*.18,-t*.11);
  vec2 q=vec2(fbm(p*1.28+drift+vec2(0.,fbm(p+t*.08))),fbm(p*1.28+vec2(5.2,1.3)-drift*.72));
  vec2 r=vec2(fbm(p*1.58+3.9*q+vec2(1.7,8.2)+t*.21),fbm(p*1.58+3.4*q+vec2(8.3,2.8)-t*.17));
  float flow=fbm(p*1.36+4.8*r+vec2(t*.13,-t*.08));
  float vein=fbm(p*3.15+2.2*r-q*1.7+vec2(-t*.18,t*.12));
  float curl=sin((flow+r.x-r.y)*8.2+p.x*1.1-t*.42)*.5+.5;
  vec3 black=vec3(.012,.014,.014), crimson=vec3(.72,.005,.012), red=vec3(1.,.055,0.);
  vec3 orange=vec3(1.,.30,.015), cream=vec3(.92,.79,.66), steel=vec3(.16,.39,.58), blue=vec3(.47,.73,.91);
  float warmField=smoothstep(.30,.71,flow+.14*curl-uv.y*.10);
  float coolField=smoothstep(.47,.77,q.y+r.x*.42+uv.y*.28)*smoothstep(.27,.64,uv.x+flow*.20);
  vec3 warm=mix(crimson,red,smoothstep(.30,.68,vein));
  warm=mix(warm,orange,smoothstep(.62,.92,flow+curl*.12));
  vec3 cool=mix(steel,blue,smoothstep(.32,.79,vein+q.x*.20));
  vec3 color=mix(black,warm,warmField);
  color=mix(color,cool,coolField*(.64+.36*smoothstep(0.,1.,curl)));
  float seam=1.-smoothstep(.035,.18,abs(fract((flow+r.x)*3.2)-.5));
  color=mix(color,cream,seam*.30*smoothstep(.25,.9,warmField+coolField));
  float leftShade=1.-smoothstep(.04,.56,uv.x+flow*.12);
  color=mix(color,black,leftShade*.90); color*=.88+.12*smoothstep(0.,1.,vein);
  gl_FragColor=vec4(color,1.);
}`;

function compile(gl,type,source){
 const item=gl.createShader(type);gl.shaderSource(item,source);gl.compileShader(item);
 if(!gl.getShaderParameter(item,gl.COMPILE_STATUS)){console.warn("Allot hero shader:",gl.getShaderInfoLog(item));gl.deleteShader(item);return null;}return item;
}

export function mountHeroFlow(canvas){
 if(!canvas)return()=>{};
 const fallback=()=>{canvas.style.background="linear-gradient(125deg,#050606 12%,#8f0710 46%,#ff4b00 67%,#78b5dd 100%)";};
 const gl=canvas.getContext("webgl",{alpha:false,antialias:false,powerPreference:"high-performance"});
 const reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
 let frame=0,visible=true,stopped=false,staticDrawn=false;
 if(!gl){fallback();return()=>{};}
 const vertex=compile(gl,gl.VERTEX_SHADER,VERTEX_SHADER),fragment=compile(gl,gl.FRAGMENT_SHADER,FRAGMENT_SHADER);
 if(!vertex||!fragment){fallback();return()=>{};}
 const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);
 if(!gl.getProgramParameter(program,gl.LINK_STATUS)){console.warn("Allot hero shader:",gl.getProgramInfoLog(program));fallback();return()=>{};}gl.useProgram(program);
 const vertices=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vertices);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
 const position=gl.getAttribLocation(program,"position");gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
 const resolution=gl.getUniformLocation(program,"resolution"),clock=gl.getUniformLocation(program,"time");
 function resize(){const rect=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,1.5),w=Math.max(1,Math.round(rect.width*dpr)),h=Math.max(1,Math.round(rect.height*dpr));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);staticDrawn=false;}}
 function draw(ms=0){resize();gl.uniform2f(resolution,canvas.width,canvas.height);gl.uniform1f(clock,reduced.matches?18:ms*.001);gl.drawArrays(gl.TRIANGLES,0,6);staticDrawn=true;if(!stopped&&visible&&!reduced.matches&&canvas.isConnected)frame=requestAnimationFrame(draw);}
 function start(){cancelAnimationFrame(frame);if(stopped||!visible)return;if(reduced.matches){if(!staticDrawn)draw(0);}else frame=requestAnimationFrame(draw);}
 const size=new ResizeObserver(()=>{staticDrawn=false;start();});
 const sight=new IntersectionObserver(([entry])=>{visible=entry?.isIntersecting??true;if(visible)start();else cancelAnimationFrame(frame);},{threshold:.02});
 const motion=()=>{staticDrawn=false;start();};size.observe(canvas);sight.observe(canvas);reduced.addEventListener?.("change",motion);draw(0);
 return()=>{stopped=true;cancelAnimationFrame(frame);size.disconnect();sight.disconnect();reduced.removeEventListener?.("change",motion);gl.deleteBuffer(vertices);gl.deleteProgram(program);gl.deleteShader(vertex);gl.deleteShader(fragment);};
}
