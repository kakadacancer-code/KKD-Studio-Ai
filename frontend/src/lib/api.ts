import axios from 'axios'
export const http = axios.create({baseURL:'/api',timeout: 120000})
export const url = (value?:string|null) => value || ''
export function errorText(e:unknown) { if (axios.isAxiosError(e)) return typeof e.response?.data?.detail === 'string' ? e.response.data.detail : e.message; return e instanceof Error ? e.message : 'Unknown error' }
export type Project = {id:string;name:string;duration:number;file_size:number;width:number;height:number;status:string;filename:string|null;video_url:string|null;created_at:string;updated_at:string;segment_count:number;translated_count:number;voiced_count:number;warning_count:number}
export type Segment = {id:number;seq:number;start:number;end:number;zh:string;km:string;translation_status:string;voice_status:string;voice_duration:number;voice_speed:number;voice_url:string|null;review_note:string}
export type Job = {id:string;project_id:string|null;kind:string;status:string;done:number;total:number;failed:number;message:string;error:string;output:string|null;created_at:string}
export type Model = {id:string;name:string;kind:string;ram:string;license:string;installed:boolean}
export type ExportResult = {id:string;filename:string;size:number;url:string;created_at:string}
export type Status = {storage_bytes:number;disk_free_bytes:number;cpu_percent:number|null;ram_percent:number|null;gpu:string;ffmpeg:boolean;active_jobs:number;models:Model[]}
export const time = (sec:number) => { const x = Math.floor(sec||0); return `${String(Math.floor(x/3600)).padStart(2,'0')}:${String(Math.floor(x/60)%60).padStart(2,'0')}:${String(x%60).padStart(2,'0')}` }
export const precise = (sec:number) => `${time(sec)}.${String(Math.round((sec%1)*1000)).padStart(3,'0')}`
export const filesize = (bytes:number) => bytes>=1e9 ? (bytes/1e9).toFixed(2)+' GB': bytes>=1e6?(bytes/1e6).toFixed(1)+' MB':(bytes/1e3).toFixed(0)+' KB'
export const jobsFor = (jobs:Job[],pid:string,kind?:string) => jobs.find(j=>j.project_id===pid&&(!kind||kind===j.kind))
