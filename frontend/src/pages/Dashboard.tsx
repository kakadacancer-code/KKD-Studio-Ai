import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import {
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  FileVideo,
  Film,
  FolderOpen,
  Languages,
  Plus,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { http, Project, time } from "../lib/api";
import {
  Empty,
  LoadingCard,
  PageTitle,
  PipelineStep,
  StatusBadge,
} from "../components/UI";
import { useStudio } from "../lib/state";

type DashboardData = {
  projects: number;
  translations: number;
  voices: number;
  video_hours: number;
  recent: Project[];
};
const steps = [
  { title: "Import video", detail: "MP4, MKV and more", icon: UploadCloud },
  {
    title: "Chinese to text",
    detail: "Faster-Whisper offline",
    icon: Languages,
  },
  { title: "Translate to Khmer", detail: "NLLB-200 model", icon: BrainCircuit },
  {
    title: "Generate & export",
    detail: "MMS voice • synced timing",
    icon: AudioLines,
  },
];
export default function Dashboard() {
  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ["dashboard"],
    queryFn: () => http.get("/dashboard").then((r) => r.data),
  });
  const nav = useNavigate();
  const setActive = useStudio((s) => s.setActiveId);
  return (
    <>
      <PageTitle
        eyebrow="Overview / 01"
        title="Good to see you in the studio."
        subtitle="Your creative space for Chinese-to-Khmer movie translation and dubbing."
      />
      <div className="relative rounded-[22px] overflow-hidden min-h-[235px] border border-violet/30 bg-[#161324] shadow-glow mb-7">
        <div
          className="absolute inset-0 opacity-60"
          style={{
            background:
              "radial-gradient(ellipse at 80% 60%,rgba(139,92,246,.31),transparent 53%),radial-gradient(ellipse at 65% -40%,rgba(56,189,248,.15),transparent 55%)",
          }}
        />
        <div className="relative z-10 p-7 sm:p-10 max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-violet/40 bg-violet/10 text-[#d9ccff] text-[11px] font-semibold py-1.5 px-3 mb-5">
            <Sparkles size={12} /> LOCAL AI · CREATIVE FREEDOM
          </span>
          <h2 className="text-3xl sm:text-[36px] font-bold tracking-tight leading-[1.16]">
            Bring Chinese Stories <br />
            <span className="text-[#ab8dff]">to Life in Khmer.</span>
          </h2>
          <p className="text-slate-400 text-sm mt-4 max-w-md leading-6">
            Translate, dub, and create Khmer movie experiences with private,
            local AI models. No paid API keys needed.
          </p>
          <div className="flex flex-wrap gap-3 mt-6">
            <Link to="/import" className="btn-primary">
              Create New Project <ArrowRight size={16} />
            </Link>
            <Link to="/projects" className="btn-ghost">
              Explore Projects
            </Link>
          </div>
        </div>
        <div
          className="hidden xl:flex absolute right-8 top-7 bottom-0 items-center gap-[5px] opacity-75"
          aria-hidden="true"
        >
          {Array.from({ length: 38 }, (_, i) => (
            <motion.div
              key={i}
              animate={{
                height: [
                  15 + Math.abs(Math.sin(i * 2)) * 60,
                  25 + Math.abs(Math.cos(i * 1.7)) * 110,
                  15 + Math.abs(Math.sin(i * 2)) * 60,
                ],
              }}
              transition={{
                duration: 2 + (i % 7) * 0.23,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              style={{
                width: 4,
                background: i % 4 === 0 ? "#38BDF8" : "#8B5CF6",
                borderRadius: 30,
              }}
            />
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-7">
        {[
          {
            label: "Total projects",
            value: data?.projects ?? 0,
            icon: FolderOpen,
            unit: "projects",
            accent: "text-[#ad93ff]",
          },
          {
            label: "Translations",
            value: data?.translations ?? 0,
            icon: Languages,
            unit: "segments",
            accent: "text-blue",
          },
          {
            label: "Voice clips ready",
            value: data?.voices ?? 0,
            icon: AudioLines,
            unit: "clips",
            accent: "text-emerald-400",
          },
          {
            label: "Processed video",
            value: data?.video_hours ?? 0,
            icon: Clock3,
            unit: "hours",
            accent: "text-amber-400",
          },
        ].map((item, i) => (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            key={item.label}
            className="card p-5 hover:border-violet/40 transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-muted text-xs">{item.label}</span>
              <item.icon className={item.accent} size={18} />
            </div>
            <div className="mt-5 flex items-baseline gap-2">
              <span className="font-bold text-3xl tabular-nums">
                {isLoading ? "—" : item.value.toLocaleString()}
              </span>
              <span className="text-muted text-xs">{item.unit}</span>
            </div>
            <div className="mt-3 h-px bg-white/[.055]" />
            <p className="mt-3 text-[11px] text-muted">
              <CheckCircle2
                size={12}
                className="inline mr-1.5 text-emerald-400"
              />
              Live local data
            </p>
          </motion.div>
        ))}
      </div>
      <div className="grid xl:grid-cols-[minmax(0,1.55fr)_minmax(290px,1fr)] gap-5">
        <section className="card p-5 sm:p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="section-title">Recent projects</h3>
              <p className="text-xs text-muted mt-1">
                Pick up exactly where you left off.
              </p>
            </div>
            <Link
              className="text-xs text-[#bca6ff] hover:underline flex items-center gap-1"
              to="/projects"
            >
              View all <ArrowUpRight size={13} />
            </Link>
          </div>
          {isLoading ? (
            <LoadingCard />
          ) : data?.recent.length ? (
            <div className="space-y-2">
              {data.recent.map((p) => (
                <button
                  onClick={() => {
                    setActive(p.id);
                    nav(`/studio/${p.id}`);
                  }}
                  className="w-full flex items-center gap-4 rounded-xl hover:bg-white/[.04] p-3 transition-colors text-left"
                  key={p.id}
                >
                  <div className="w-14 h-12 shrink-0 rounded-lg bg-[#232038] border border-violet/15 flex justify-center items-center text-[#bca6ff]">
                    <Film size={21} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-sm truncate">{p.name}</p>
                    <p className="text-xs text-muted mt-1">
                      {time(p.duration)} · {p.segment_count} dialogue segments
                    </p>
                  </div>
                  <div className="hidden sm:block">
                    <StatusBadge status={p.status} />
                  </div>
                  <ArrowRight size={16} className="text-muted" />
                </button>
              ))}
            </div>
          ) : (
            <Empty
              icon={FileVideo}
              title="Your first story starts here"
              body="Import a short Chinese video and KKD Studio will guide you through the workflow."
            >
              <Link className="btn-primary" to="/import">
                <Plus size={16} /> Import your first video
              </Link>
            </Empty>
          )}
        </section>
        <section className="card p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="section-title">Your workflow</h3>
              <p className="text-xs text-muted mt-1">
                Four steps to Khmer dubbing.
              </p>
            </div>
            <div className="rounded-lg bg-violet/10 p-2 text-violet">
              <Film size={18} />
            </div>
          </div>
          <div className="mt-4 divide-y divide-edge/60">
            {steps.map((s, i) => (
              <PipelineStep
                key={s.title}
                number={i + 1}
                label={s.title}
                detail={s.detail}
              />
            ))}
          </div>
          <div className="mt-4 rounded-xl border border-blue/20 bg-blue/5 p-3 flex gap-3 items-start">
            <ShieldCheck size={17} className="text-blue shrink-0 mt-0.5" />
            <p className="text-xs text-slate-300 leading-5">
              Start with a <b>1–5 minute video</b>. Long films work best once
              you’ve checked your CPU performance, model downloads and
              translation quality.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
