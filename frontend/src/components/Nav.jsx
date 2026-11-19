import { NavLink } from "react-router"

const LINKS = [["/", "Instagram + YouTube"], ["/meta", "Insta - Face - Threads"], ["/youtube", "YouTube"]]

export default function Nav() {
  return (
    <nav className="nav">
      <span className="nav-brand">DGM Publishing Hub</span>
      <div className="nav-links">
        {LINKS.map(([to, label]) => (
          <NavLink key={to} to={to} end className={({ isActive }) => `nav-link${isActive ? " nav-link--on" : ""}`}>{label}</NavLink>
        ))}
      </div>
    </nav>
  )
}
