import type { SkillCard } from '../../types/console'
import { formatDate, formatScore } from './formatters'

type SkillSnapshotProps = {
  skills: SkillCard[]
}

function SkillSnapshot({ skills }: SkillSnapshotProps) {
  const topSkills = [...skills]
    .filter((skill) => skill.latest_round !== null)
    .sort((left, right) => (right.latest_round?.score ?? 0) - (left.latest_round?.score ?? 0))
    .slice(0, 3)

  return (
    <section className="skill-snapshot panel">
      <div className="section-heading inline">
        <div>
          <span className="eyebrow">Skill snapshot</span>
          <h2>Top governed generators</h2>
        </div>
        <a className="text-link" href="/console/trust">View all skills</a>
      </div>
      <div className="skill-list">
        {topSkills.length ? (
          topSkills.map((skill) => (
            <article key={skill.skill_id} className="skill-row">
              <div>
                <strong>{skill.display_name}</strong>
                <p>{skill.skill_id}</p>
              </div>
              <div className="skill-row-meta">
                <span>{formatScore(skill.latest_round?.score)}</span>
                <time>{formatDate(skill.latest_round?.completed_at ?? null)}</time>
              </div>
            </article>
          ))
        ) : (
          <div className="empty-state compact">
            <h3>No skill measurements</h3>
            <p>Run eval rounds to see governed generator health.</p>
          </div>
        )}
      </div>
    </section>
  )
}

export default SkillSnapshot
