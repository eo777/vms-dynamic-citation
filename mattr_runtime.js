/* Playback owns its timers. URL persistence happens only after interaction settles. */
"use strict";
const SG_MATTR_RUNTIME=(()=>{
 function playback({step,interval,onState,onPause,save,onError,later=setTimeout,cancel=clearTimeout,saveDelay=180}){
  let playing=false,epoch=0,timer=null,saveTimer=null;
  function saveSoon(){
   if(playing)return;
   cancel(saveTimer);saveTimer=later(()=>{saveTimer=null;if(!playing)save();},saveDelay);
  }
  function pause(){
   playing=false;epoch++;cancel(timer);timer=null;onState(false);onPause();saveSoon();
  }
  function tick(ticket){
   if(!playing||ticket!==epoch)return;
   timer=null;
   try{if(step()===false){pause();return;}}
   catch(error){pause();if(onError)onError(error);else throw error;return;}
   if(playing&&ticket===epoch)timer=later(()=>tick(ticket),interval());
  }
  function play(){
   if(playing)return;
   cancel(saveTimer);saveTimer=null;playing=true;const ticket=++epoch;onState(true);
   timer=later(()=>tick(ticket),interval());
  }
  return {play,pause,saveSoon,get playing(){return playing;}};
 }
 return {playback};
})();
if(typeof module!=='undefined')module.exports=SG_MATTR_RUNTIME;
