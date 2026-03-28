import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
// eslint-disable-next-line no-unused-vars
import { motion, useInView, useScroll, useTransform } from 'framer-motion';
import {
  Zap, Target, Users, Search, Send, BarChart3, ArrowRight,
  Sparkles, Bot, TrendingUp, Shield, Clock, Brain, Mail,
  ChevronRight, Star, CheckCircle2, Play, MousePointer2,
} from 'lucide-react';

/* ── Animated counter ── */
function Counter({ target, suffix = '', duration = 2000 }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-50px' });

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const step = target / (duration / 16);
    const id = setInterval(() => {
      start += step;
      if (start >= target) { setCount(target); clearInterval(id); }
      else setCount(Math.floor(start));
    }, 16);
    return () => clearInterval(id);
  }, [inView, target, duration]);

  return <span ref={ref}>{count.toLocaleString()}{suffix}</span>;
}

/* ── Floating shapes (decorative) ── */
function FloatingShape({ className, delay = 0, children }) {
  return (
    <motion.div
      className={`absolute pointer-events-none ${className}`}
      animate={{ y: [0, -20, 0], rotate: [0, 5, -5, 0] }}
      transition={{ duration: 6, repeat: Infinity, delay, ease: 'easeInOut' }}
    >
      {children}
    </motion.div>
  );
}

/* ── Pipeline stage card ── */
const stages = [
  { icon: Target, label: 'ICP Setup', desc: 'Define your ideal customer profile with AI-assisted targeting', color: 'bg-electric-blue', shadow: 'shadow-[4px_4px_0_#1e3a5f]' },
  { icon: Users, label: 'Prospecting', desc: 'Discover high-fit companies from 8+ free data sources', color: 'bg-accent-yellow', shadow: 'shadow-[4px_4px_0_#1e3a5f]' },
  { icon: Search, label: 'Research', desc: 'Deep-dive dossiers with tech stack, news & pain points', color: 'bg-sky-blue', shadow: 'shadow-[4px_4px_0_#1e3a5f]' },
  { icon: Send, label: 'Outreach', desc: 'AI-personalised emails with one-click send & manual compose', color: 'bg-accent-green', shadow: 'shadow-[4px_4px_0_#1e3a5f]' },
  { icon: BarChart3, label: 'Tracking', desc: 'Monitor opens, replies & follow-ups in real time', color: 'bg-accent-orange', shadow: 'shadow-[4px_4px_0_#1e3a5f]' },
];

function StageCard({ stage, index }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 60, rotate: -2 }}
      animate={inView ? { opacity: 1, y: 0, rotate: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.12 }}
      className="relative group"
    >
      {/* Connector line */}
      {index < stages.length - 1 && (
        <div className="hidden lg:block absolute top-1/2 -right-8 w-8 border-t-[3px] border-dashed border-border-brutal" />
      )}
      <div className={`neu-card p-6 h-full cursor-default`}>
        <div className="flex items-start gap-4">
          <div className={`p-3 rounded-xl ${stage.color} border-[2.5px] border-border-brutal ${stage.shadow} shrink-0 group-hover:scale-110 transition-transform`}>
            <stage.icon className="w-6 h-6 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Stage {index + 1}</span>
            </div>
            <h3 className="text-lg font-bold text-display text-deep-blue mb-1">{stage.label}</h3>
            <p className="text-sm text-slate-500 leading-relaxed">{stage.desc}</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

/* ── Feature highlight ── */
const features = [
  { icon: Bot, title: 'AI-Powered Pipeline', desc: 'End-to-end automation from ICP to personalised outreach', color: 'text-electric-blue' },
  { icon: Brain, title: 'Smart Personalisation', desc: 'Every email is crafted with research signals & AI enhancement', color: 'text-purple-500' },
  { icon: Shield, title: 'Human-in-the-Loop', desc: 'Nothing sends without your approval — full review control', color: 'text-accent-green' },
  { icon: Clock, title: 'Minutes, Not Hours', desc: 'What takes SDRs days happens in minutes with parallel agents', color: 'text-accent-orange' },
  { icon: Mail, title: 'Manual + AI Compose', desc: 'Add your own recipients and let AI polish the messaging', color: 'text-sky-blue' },
  { icon: TrendingUp, title: 'Real-Time Tracking', desc: 'Monitor delivery, opens, replies and auto-generate follow-ups', color: 'text-accent-red' },
];

/* ── Typewriter text ── */
function Typewriter({ words, className }) {
  const [index, setIndex] = useState(0);
  const [displayed, setDisplayed] = useState('');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const word = words[index];
    const speed = deleting ? 40 : 80;

    if (!deleting && displayed === word) {
      const t = setTimeout(() => setDeleting(true), 2000);
      return () => clearTimeout(t);
    }
    if (deleting && displayed === '') {
      const t = setTimeout(() => {
        setDeleting(false);
        setIndex((index + 1) % words.length);
      }, 0);
      return () => clearTimeout(t);
    }

    const t = setTimeout(() => {
      setDisplayed(deleting ? word.slice(0, displayed.length - 1) : word.slice(0, displayed.length + 1));
    }, speed);
    return () => clearTimeout(t);
  }, [displayed, deleting, index, words]);

  return (
    <span className={className}>
      {displayed}
      <span className="animate-pulse">|</span>
    </span>
  );
}

/* ── Orbiting dot animation ── */
function OrbitingDots() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {[...Array(5)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-3 h-3 rounded-full border-2 border-border-brutal"
          style={{
            background: ['#3b82f6', '#facc15', '#22c55e', '#f97316', '#60a5fa'][i],
            top: `${20 + i * 15}%`,
            left: `${10 + i * 18}%`,
          }}
          animate={{
            x: [0, 30 * (i % 2 === 0 ? 1 : -1), 0],
            y: [0, -25 * (i % 2 === 0 ? -1 : 1), 0],
            scale: [1, 1.3, 1],
          }}
          transition={{ duration: 4 + i, repeat: Infinity, ease: 'easeInOut', delay: i * 0.5 }}
        />
      ))}
    </div>
  );
}

/* ════════════════════════════════════════════════════════
   LANDING PAGE
   ════════════════════════════════════════════════════════ */
export default function Landing() {
  const navigate = useNavigate();
  const { scrollYProgress } = useScroll();
  const heroScale = useTransform(scrollYProgress, [0, 0.15], [1, 0.96]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);

  const featuresRef = useRef(null);
  const featuresInView = useInView(featuresRef, { once: true, margin: '-100px' });

  return (
    <div className="min-h-screen overflow-x-hidden">
      {/* ── Navbar ── */}
      <motion.nav
        initial={{ y: -80 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b-[3px] border-border-brutal"
      >
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-electric-blue border-[2.5px] border-border-brutal flex items-center justify-center shadow-[3px_3px_0_var(--color-border-brutal)]">
              <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <div>
              <span className="text-lg font-bold text-display text-deep-blue">SalesAI</span>
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest ml-2">Pipeline</span>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-semibold text-slate-500">
            <a href="#features" className="hover:text-deep-blue transition-colors">Features</a>
            <a href="#pipeline" className="hover:text-deep-blue transition-colors">Pipeline</a>
            <a href="#stats" className="hover:text-deep-blue transition-colors">Results</a>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="neu-btn bg-electric-blue text-white px-5 py-2 text-sm flex items-center gap-2 hover:bg-blue-600"
          >
            Open Dashboard <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </motion.nav>

      {/* ── Hero Section ── */}
      <motion.section
        style={{ scale: heroScale, opacity: heroOpacity }}
        className="relative pt-32 pb-20 px-6 min-h-[95vh] flex items-center"
      >
        <OrbitingDots />

        {/* Decorative floating shapes */}
        <FloatingShape className="top-28 left-[8%]" delay={0}>
          <div className="w-16 h-16 rounded-2xl bg-accent-yellow/20 border-[2.5px] border-accent-yellow rotate-12" />
        </FloatingShape>
        <FloatingShape className="top-40 right-[10%]" delay={1}>
          <div className="w-12 h-12 rounded-full bg-accent-green/20 border-[2.5px] border-accent-green" />
        </FloatingShape>
        <FloatingShape className="bottom-32 left-[15%]" delay={2}>
          <div className="w-10 h-10 rounded-xl bg-electric-blue/20 border-[2.5px] border-electric-blue -rotate-12" />
        </FloatingShape>
        <FloatingShape className="bottom-40 right-[12%]" delay={0.5}>
          <div className="w-14 h-14 rounded-2xl bg-accent-orange/20 border-[2.5px] border-accent-orange rotate-6" />
        </FloatingShape>

        <div className="max-w-7xl mx-auto text-center relative z-10">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-yellow/10 border-[2.5px] border-accent-yellow text-deep-blue text-sm font-bold mb-8 shadow-[3px_3px_0_var(--color-border-brutal)]"
          >
            <Sparkles className="w-4 h-4 text-accent-yellow" />
            AI-Powered Sales Intelligence
            <ChevronRight className="w-4 h-4" />
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.7 }}
            className="text-5xl md:text-7xl lg:text-8xl font-bold text-display text-deep-blue leading-[1.05] mb-6 max-w-5xl mx-auto"
          >
            Turn Cold Leads{' '}
            <span className="relative inline-block">
              <span className="relative z-10">Into Warm</span>
              <motion.span
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ delay: 0.9, duration: 0.5 }}
                className="absolute bottom-1 left-0 right-0 h-4 bg-accent-yellow/40 z-0 origin-left rounded"
              />
            </span>
            <br />
            <Typewriter
              words={['Conversations', 'Opportunities', 'Revenue', 'Partnerships']}
              className="text-electric-blue"
            />
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.55, duration: 0.6 }}
            className="text-lg md:text-xl text-slate-500 max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            5-stage AI pipeline that discovers prospects, researches companies,
            writes personalised emails, and tracks every interaction — all on autopilot.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.5 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <button
              onClick={() => navigate('/dashboard')}
              className="neu-btn bg-electric-blue text-white px-8 py-4 text-lg flex items-center gap-3 hover:bg-blue-600 group"
            >
              <Play className="w-5 h-5 group-hover:scale-110 transition-transform" strokeWidth={2.5} />
              Launch Dashboard
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <a
              href="#pipeline"
              className="neu-btn bg-white text-deep-blue px-8 py-4 text-lg flex items-center gap-3 hover:bg-slate-50"
            >
              <MousePointer2 className="w-5 h-5" strokeWidth={2.5} />
              See How It Works
            </a>
          </motion.div>

          {/* Hero visual — animated pipeline preview */}
          <motion.div
            initial={{ opacity: 0, y: 60 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1, duration: 0.8 }}
            className="mt-16 max-w-4xl mx-auto"
          >
            <div className="neu-card-flat p-2 overflow-hidden">
              <div className="bg-linear-to-br from-slate-50 to-blue-50 rounded-xl p-6 relative">
                {/* Mini pipeline visualization */}
                <div className="flex items-center justify-between gap-2">
                  {stages.map((s, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, scale: 0.5 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 1.3 + i * 0.15 }}
                      className="flex-1 text-center"
                    >
                      <motion.div
                        animate={{ y: [0, -6, 0] }}
                        transition={{ duration: 2, delay: i * 0.3, repeat: Infinity, ease: 'easeInOut' }}
                        className={`w-12 h-12 mx-auto rounded-xl ${s.color} border-[2.5px] border-border-brutal ${s.shadow} flex items-center justify-center mb-2`}
                      >
                        <s.icon className="w-5 h-5 text-white" strokeWidth={2.5} />
                      </motion.div>
                      <p className="text-[11px] font-bold text-slate-600 text-display">{s.label}</p>
                      {i < stages.length - 1 && (
                        <motion.div
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: 1 }}
                          transition={{ delay: 1.5 + i * 0.2, duration: 0.4 }}
                          className="absolute top-10.5 w-6 border-t-2 border-dashed border-slate-300"
                          style={{ left: `${(i + 1) * 20 - 2}%` }}
                        />
                      )}
                    </motion.div>
                  ))}
                </div>

                {/* Animated scan line */}
                <motion.div
                  className="absolute top-0 left-0 w-1 h-full bg-linear-to-b from-transparent via-electric-blue to-transparent opacity-30"
                  animate={{ x: ['0%', '4000%'] }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'linear', repeatDelay: 1 }}
                />
              </div>
            </div>
          </motion.div>
        </div>
      </motion.section>

      {/* ── Stats Section ── */}
      <section id="stats" className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { value: 8, suffix: '+', label: 'Data Sources', color: 'bg-electric-blue' },
              { value: 95, suffix: '%', label: 'Time Saved', color: 'bg-accent-green' },
              { value: 500, suffix: '+', label: 'Prospects / Run', color: 'bg-accent-yellow' },
              { value: 3, suffix: 'x', label: 'Reply Rate Boost', color: 'bg-accent-orange' },
            ].map((stat, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 40, rotate: -3 }}
                whileInView={{ opacity: 1, y: 0, rotate: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ delay: i * 0.1 }}
                className="neu-card p-6 text-center"
              >
                <p className="text-4xl md:text-5xl font-bold text-display text-deep-blue mb-1">
                  <Counter target={stat.value} suffix={stat.suffix} />
                </p>
                <div className={`inline-block px-3 py-1 rounded-lg text-xs font-bold text-white ${stat.color} border-2 border-border-brutal`}>
                  {stat.label}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pipeline Section ── */}
      <section id="pipeline" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-14"
          >
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-blue/10 border-2 border-sky-blue text-sky-blue text-xs font-bold uppercase tracking-wider mb-4">
              <Zap className="w-3 h-3" /> The Pipeline
            </span>
            <h2 className="text-4xl md:text-5xl font-bold text-display text-deep-blue mb-4">
              Five Stages. Zero Busywork.
            </h2>
            <p className="text-lg text-slate-500 max-w-xl mx-auto">
              Each stage runs in parallel with AI agents that handle the heavy lifting while you stay in control.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 lg:gap-4">
            {stages.map((stage, i) => (
              <StageCard key={i} stage={stage} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ── Features Grid ── */}
      <section id="features" className="py-20 px-6 bg-white border-y-[3px] border-border-brutal">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-14"
          >
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-green/10 border-2 border-accent-green text-accent-green text-xs font-bold uppercase tracking-wider mb-4">
              <Sparkles className="w-3 h-3" /> Features
            </span>
            <h2 className="text-4xl md:text-5xl font-bold text-display text-deep-blue mb-4">
              Built for Modern Sales Teams
            </h2>
            <p className="text-lg text-slate-500 max-w-xl mx-auto">
              Everything you need to run intelligent, personalised outreach at scale.
            </p>
          </motion.div>

          <div ref={featuresRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 40 }}
                animate={featuresInView ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: i * 0.1, duration: 0.5 }}
                className="neu-card p-6 group"
              >
                <div className="flex items-start gap-4">
                  <div className={`p-2.5 rounded-xl bg-slate-50 border-2 border-slate-200 group-hover:border-border-brutal group-hover:shadow-[3px_3px_0_var(--color-border-brutal)] transition-all ${f.color}`}>
                    <f.icon className="w-5 h-5" strokeWidth={2.5} />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-display text-deep-blue mb-1">{f.title}</h3>
                    <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Compares ── */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-14"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-display text-deep-blue mb-4">
              Manual SDR vs SalesAI
            </h2>
            <p className="text-lg text-slate-500">
              See the difference AI-powered prospecting makes.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Manual */}
            <motion.div
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="neu-card-flat p-6 bg-red-50/50"
            >
              <h3 className="text-lg font-bold text-display text-slate-600 mb-4 flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-red border-2 border-border-brutal">
                  <Clock className="w-4 h-4 text-white" />
                </div>
                Traditional SDR
              </h3>
              <ul className="space-y-3">
                {[
                  '4+ hours researching per prospect',
                  'Copy-paste email templates',
                  'Manual data entry across tools',
                  'Generic outreach, low reply rates',
                  'No visibility into what works',
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-500">
                    <span className="w-5 h-5 rounded-md bg-red-100 border border-red-200 flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-accent-red text-xs font-bold">✕</span>
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
            </motion.div>

            {/* SalesAI */}
            <motion.div
              initial={{ opacity: 0, x: 40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="neu-card p-6 bg-green-50/50 border-accent-green"
            >
              <h3 className="text-lg font-bold text-display text-deep-blue mb-4 flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-accent-green border-2 border-border-brutal shadow-[2px_2px_0_var(--color-border-brutal)]">
                  <Zap className="w-4 h-4 text-white" />
                </div>
                SalesAI Pipeline
              </h3>
              <ul className="space-y-3">
                {[
                  'Research 100+ prospects in minutes',
                  'AI-personalised emails with real signals',
                  'Automated enrichment from 8+ sources',
                  '3x higher reply rate with relevance',
                  'Full tracking & intelligent follow-ups',
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600 font-medium">
                    <CheckCircle2 className="w-5 h-5 text-accent-green shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── CTA Section ── */}
      <section className="py-24 px-6 relative overflow-hidden">
        <OrbitingDots />
        <div className="max-w-3xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="neu-card p-10 md:p-14 bg-linear-to-br from-deep-blue to-[#2a4f7a]"
          >
            <motion.div
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 4, repeat: Infinity }}
              className="inline-flex p-4 rounded-2xl bg-accent-yellow border-[3px] border-white/20 shadow-[4px_4px_0_rgba(0,0,0,0.3)] mb-6"
            >
              <Zap className="w-8 h-8 text-deep-blue" strokeWidth={2.5} />
            </motion.div>
            <h2 className="text-3xl md:text-5xl font-bold text-display text-white mb-4">
              Ready to Supercharge<br />Your Sales Pipeline?
            </h2>
            <p className="text-lg text-blue-200 mb-8 max-w-lg mx-auto">
              Stop wasting time on manual prospecting. Let AI agents do the heavy lifting while you close deals.
            </p>
            <button
              onClick={() => navigate('/dashboard')}
              className="neu-btn bg-accent-yellow text-deep-blue px-10 py-4 text-lg font-bold flex items-center gap-3 mx-auto hover:bg-yellow-400 group"
            >
              <Play className="w-5 h-5" strokeWidth={2.5} />
              Open Dashboard Now
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
          </motion.div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t-[3px] border-border-brutal py-8 px-6 bg-white">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-electric-blue border-2 border-border-brutal flex items-center justify-center shadow-[2px_2px_0_var(--color-border-brutal)]">
              <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <span className="font-bold text-display text-deep-blue">SalesAI Pipeline</span>
          </div>
          <p className="text-sm text-slate-400">
            Built with AI agents &middot; Powered by LLMs &middot; Designed for modern sales
          </p>
          <div className="flex items-center gap-1">
            {[...Array(5)].map((_, i) => (
              <Star key={i} className="w-4 h-4 text-accent-yellow fill-accent-yellow" />
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
