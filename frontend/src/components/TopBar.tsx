import {Outlet, NavLink} from "react-router-dom"
import { useState } from "react"
import { useNavigate } from "react-router-dom"

import SPbguLogo from "../assets/spbgu_logo.svg"
import OP_logo from "../assets/OP_logo.svg"
import {  BACKEND_URL,RED } from "../config.ts"

function TopBarLayout() {
    const [menuOpen, setMenuOpen] = useState(false)

    const navLinkClass = ({isActive}: { isActive: boolean }) =>
        `
    relative pb-1
    transition-colors duration-200
    hover:text-gray-900

    after:content-['']
    after:absolute
    after:left-0
    after:bottom-0
    after:h-[2px]
    after:w-full
    after:bg-[#9F2D20]
    after:origin-left
    after:transition-transform
    after:duration-200

    ${isActive ? "after:scale-x-100" : "after:scale-x-0"}
  `

    const NAV_ITEMS = [
        {to: "/event", label: "Журнал", end: true},
        {to: "/safety", label: "Безопасность"},
        {to: "/telemetry", label: "Телеметрия"},
        {to: "/commands", label: "Аналитика команд"},
        {to: "/about", label: "О нас"},
    ]

    const navigate = useNavigate()

    const handleLogout = async () => {
        const access = localStorage.getItem("access_token")
        try {
            if (access) {
                await fetch(`${BACKEND_URL}/auth/logout`, {
                    method: "POST",
                    credentials: "include",
                    headers: {
                        Authorization: `Bearer ${access}`,
                    },
                })
            }
        } catch {
            /* network errors: still clear client session */
        } finally {
            localStorage.removeItem("access_token")
            navigate("/login")
        }
    }

    return (
        <div className="min-h-screen flex flex-col bg-white text-gray-800">
            <header
                className="fixed top-0 left-0 right-0 h-16 flex items-center justify-between px-8 shadow-sm border-b bg-white z-50">
                <div className="flex items-center gap-3 flex-shrink-0">
                    <img src={OP_logo} alt="OP Logo" className="h-9 ml-3"/>

                    <span className="text-sm font-semibold tracking-tight  leading-none hidden sm:block">
            <span style={{color: RED}}>OurPaint</span> <br />Company
          </span>

                    <img src={SPbguLogo} alt="SPbGU Logo" className="h-20 ml-3"/>
                </div>

                <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
                    {NAV_ITEMS.map(({to, label, end}) => (
                        <NavLink key={to} to={to} end={end} className={navLinkClass}>
                            {label}
                        </NavLink>
                    ))}

                    <button
                        className="ml-4 px-4 py-2 rounded-lg text-white transition-colors duration-200"
                        style={{ backgroundColor: RED }}
                        onClick={handleLogout}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#87251B")}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = RED)}
                    >
                        Выйти
                    </button>
                </nav>

                <button
                    className="md:hidden p-2"
                    onClick={() => setMenuOpen(prev => !prev)}
                >
                    <svg
                        className="w-6 h-6"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        viewBox="0 0 24 24"
                    >
                        {menuOpen ? (
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        ) : (
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                        )}
                    </svg>
                </button>
            </header>

            {menuOpen && (
                <div className="md:hidden fixed top-16 left-0 right-0 bg-white shadow-md flex flex-col gap-4 p-4 z-40">
                    {NAV_ITEMS.map(({ to, label, end }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={end}
                            className={navLinkClass}
                            onClick={() => setMenuOpen(false)}
                        >
                            {label}
                        </NavLink>
                    ))}

                    <button
                        className="px-4 py-2 rounded-lg text-white transition-colors duration-200"
                        style={{ backgroundColor: RED }}
                        onClick={() => {
                            setMenuOpen(false)
                            handleLogout()
                        }}
                    >
                        Выйти
                    </button>
                </div>
            )}

            <main className="flex-1 pt-16">
                <Outlet/>
            </main>
        </div>
    )
}

export default TopBarLayout
