import {create} from 'zustand'
import {persist} from 'zustand/middleware'
type Store = {activeId:string|null;setActiveId:(id:string|null)=>void;whisper:string;setWhisper:(model:string)=>void;compact:boolean;setCompact:(value:boolean)=>void}
export const useStudio = create<Store>()(persist(set=>({activeId:null,setActiveId:id=>set({activeId:id}),whisper:'base',setWhisper:model=>set({whisper:model}),compact:false,setCompact:value=>set({compact:value})}),{name:'kkd-studio-settings'}))
