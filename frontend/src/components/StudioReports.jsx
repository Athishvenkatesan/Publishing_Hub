// Analytics reports: headline numbers, one metric over time, and ranked breakdowns. One colour; no dual axes.
import { useState } from "react"
import { Banner } from "@astryxdesign/core/Banner"
import { Button } from "@astryxdesign/core/Button"
import { SegmentedControl, SegmentedControlItem } from "@astryxdesign/core/SegmentedControl"
import { Spinner } from "@astryxdesign/core/Spinner"
import { Text } from "@astryxdesign/core/Text"
import { connectAccount_, studioReports, studioUrl } from "../lib/api.js"
import { AGE, TRAFFIC, compact, duration, label, longDate } from "../lib/format.js"
import { useLoad } from "../lib/useLoad.js"
import BarList from "./charts/BarList.jsx"
import LineChart from "./charts/LineChart.jsx"
import StatTile from "./charts/StatTile.jsx"

const METRICS = [["views", "Views"], ["watchHours", "Watch time (hours)"], ["netSubscribers", "Net subscribers"], ["likes", "Likes"], ["comments", "Comments"], ["shares", "Shares"]]
const region = (() => { try { return new Intl.DisplayNames(["en"], { type: "region" }) } catch { return null } })()
const sample = (a, n = 12) => (a.length <= n ? a : Array.from({ length: n }, (_, i) => a[Math.round((i / (n - 1)) * (a.length - 1))]))
const sum = (rows, k, v) => Object.entries(rows.reduce((m, r) => ({ ...m, [r[k]]: (m[r[k]] || 0) + r[v] }), {}))

function Card({ title, csv, days, children }) {
  return (
    <section className="panel">
      <div className="panel-head"><Text weight="semibold">{title}</Text>
        <a className="linkbtn no-print" href={studioUrl(`reports.csv?report=${csv}&days=${days}`)}>Download CSV</a></div>
      {children}
    </section>
  )
}

function Problem({ problem }) {
  return problem.code === "api_disabled" ? (
    <Banner status="warning" title="Turn on the YouTube Analytics API" description="Reports use a second Google API. In Google Cloud, open the library, find YouTube Analytics API for this project and press Enable. Then check again." />
  ) : (
    <Banner status="info" title="Reports need one more permission" description="Your Google account has not allowed this app to read analytics yet." />
  )
}

export default function StudioReports({ account }) {
  const [days, setDays] = useState(28)
  const [metric, setMetric] = useState("views")
  const { data, error, loading, reload } = useLoad(() => studioReports(days), [account, days])
  const go = async (opts) => { window.location.href = (await connectAccount_(account, opts, "studio")).url }

  if (error) return <Banner status="error" title="Could not load reports" description={error} />
  if (!data) return <div className="working"><Spinner /><Text size="sm">Reading reports from YouTube...</Text></div>
  if (!data.available) {
    return (
      <div className="stack">
        <Problem problem={data.problem} />
        <div className="row-btns">
          {data.problem.code === "scope" && <Button label="Add the reports permission" onClick={() => go({ reports: true })} />}
          {data.problem.code === "api_disabled" && <a className="btn-link" href="https://console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com" target="_blank" rel="noreferrer">Open the Analytics API page</a>}
          <Button variant="secondary" label="Check again" isLoading={loading} onClick={reload} />
        </div>
      </div>
    )
  }
  const t = data.totals, p = data.previous, d = data.daily
  const series = d.map((r) => ({ x: r.day, y: r[metric] ?? 0 }))
  const age = sum(data.demographics, "ageGroup", "viewerPercentage").sort(([a], [b]) => a.localeCompare(b))
  const pct = (v) => `${v.toFixed(1)}%`
  return (
    <div className={`stack${loading ? " is-loading" : ""}`}>
      <div className="filters no-print">
        <SegmentedControl label="Period" value={String(days)} onChange={(v) => setDays(Number(v))}>
          {[7, 28, 90, 365].map((n) => <SegmentedControlItem key={n} value={String(n)} label={n === 365 ? "Last year" : `Last ${n} days`} />)}
        </SegmentedControl>
        <Button variant="secondary" size="sm" label="Print or save as PDF" onClick={() => window.print()} />
        <a className="linkbtn" href={studioUrl(`reports.csv?report=daily&days=${days}`)}>Download all days (CSV)</a>
      </div>
      <Text size="sm" color="secondary">{longDate(data.range.start)} to {longDate(data.range.end)}, compared with the {days} days before. The newest days can be incomplete.</Text>
      <div className="tiles">
        {METRICS.map(([k, name]) => <StatTile key={k} label={name} value={compact(t[k])} cur={t[k]} prev={p[k]} spark={sample(d.map((r) => r[k] ?? 0))} active={metric === k} onClick={() => setMetric(k)} />)}
        <StatTile label="Average view duration" value={duration(t.averageViewDuration || 0)} cur={t.averageViewDuration} prev={p.averageViewDuration} />
      </div>
      <section className="panel"><Text weight="semibold">{METRICS.find((m) => m[0] === metric)[1]} per day</Text><LineChart data={series} name={METRICS.find((m) => m[0] === metric)[1]} /></section>
      <div className="cards">
        <Card title="Top videos" csv="videos" days={days}><BarList rows={data.top_videos.map((v) => ({ key: v.video, label: v.title, value: v.views, note: `${compact(v.estimatedMinutesWatched / 60)} hours watched` }))} /></Card>
        <Card title="Where viewers find you" csv="traffic" days={days}><BarList rows={data.traffic.map((r) => ({ label: label(TRAFFIC, r.insightTrafficSourceType), value: r.views }))} /></Card>
        <Card title="Top countries" csv="countries" days={days}><BarList rows={data.countries.map((r) => ({ label: region?.of(r.country) || r.country, value: r.views }))} /></Card>
        <Card title="Devices" csv="devices" days={days}><BarList rows={data.devices.map((r) => ({ label: label({}, r.deviceType), value: r.views }))} /></Card>
        <Card title="Audience by age" csv="demographics" days={days}><BarList format={pct} empty="YouTube shows age and gender once enough people watch." rows={age.map(([k, v]) => ({ label: AGE(k), value: v }))} /></Card>
        <Card title="Audience by gender" csv="demographics" days={days}><BarList format={pct} empty="YouTube shows age and gender once enough people watch." rows={sum(data.demographics, "gender", "viewerPercentage").map(([k, v]) => ({ label: k.replace(/^./, (c) => c.toUpperCase()), value: v }))} /></Card>
      </div>
    </div>
  )
}
