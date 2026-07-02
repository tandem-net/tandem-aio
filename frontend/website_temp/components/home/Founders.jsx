"use client";

import { motion } from "framer-motion";
import { FOUNDERS } from "@/lib/data";
import { fadeUp, scaleIn, staggerParent, viewportConfig } from "@/lib/motion";
import GlassCard from "@/components/ui/GlassCard";
import SectionLabel from "@/components/ui/SectionLabel";

export default function Founders() {
  return (
    <section id="founders" className="relative overflow-hidden bg-obsidian-950 px-6 py-28 lg:py-40">
      <div
        aria-hidden="true"
        className="absolute left-1/2 top-1/2 -z-10 h-[34rem] w-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(46,155,255,0.06)_0%,transparent_68%)]"
      />

      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-2xl text-center">
          <div className="flex justify-center">
            <SectionLabel>Founders</SectionLabel>
          </div>
          <motion.h2
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={viewportConfig}
            className="mt-6 text-section font-semibold text-mist-50"
          >
            Six builders shaping a quieter cloud.
          </motion.h2>
          <motion.p
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={viewportConfig}
            className="mx-auto mt-5 max-w-2xl text-balance text-lg leading-relaxed text-mist-400"
          >
            Tandem is being built by a distributed team focused on private compute, secure collaboration, and practical deployment.
          </motion.p>
        </div>

        <motion.div
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={viewportConfig}
          className="mt-16 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3"
        >
          {FOUNDERS.map((founder) => (
            <motion.div key={founder.id} variants={scaleIn}>
              <GlassCard interactive className="h-full p-7">
                <div className="flex h-11 w-11 items-center justify-center rounded-full border border-white/10 bg-white/5 text-[15px] font-semibold text-accent-blue">
                  {founder.name
                    .split(" ")
                    .map((part) => part[0])
                    .slice(0, 2)
                    .join("")}
                </div>
                <h3 className="mt-5 text-[17px] font-semibold tracking-tight text-mist-50">
                  {founder.name}
                </h3>
                <p className="mt-1 text-[13px] text-accent-blue">{founder.role}</p>
                <p className="mt-3 text-[14px] leading-relaxed text-mist-400">
                  {founder.bio}
                </p>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
