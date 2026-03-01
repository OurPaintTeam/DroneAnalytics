import {Outlet, NavLink} from "react-router-dom"
import SPbguLogo from "../assets/spbgu_logo.svg"
import OP_logo from "../assets/OP_logo.svg"
import { RED } from "../config.ts"

function TopBarLayout() {
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
        {to: "/log", label: "Журнал", end: true},
        {to: "/security", label: "Безопасность"},
        {to: "/telemetry", label: "Телеметрия"},
        {to: "/commands", label: "Аналитика команд"},
        {to: "/about", label: "О нас"},
    ]

    return (
        <div className="min-h-screen flex flex-col bg-white text-gray-800">
            {/* TOP BAR */}
            <header
                className="fixed top-0 left-0 right-0 h-16 flex items-center justify-between px-8 shadow-sm border-b bg-white z-50">

                {/* Logo */}
                <div className="flex items-center gap-3 flex-shrink-0">
                    <img src={OP_logo} alt="OP Logo" className="h-9 ml-3"/>

                    <span className="text-sm font-semibold tracking-tight  leading-none hidden sm:block">
            <span style={{color: RED}}>OurPaint</span> <br />Company
          </span>

                    <img src={SPbguLogo} alt="SPbGU Logo" className="h-20 ml-3"/>
                </div>

                {/* Navigation */}
                <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
                    {NAV_ITEMS.map(({to, label, end}) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={end}
                            className={navLinkClass}
                        >
                            {label}
                        </NavLink>
                    ))}

                    {/* Logout button */}
                    <NavLink
                        to="/login"
                        className="ml-4 px-4 py-2 rounded-lg text-white transition-colors duration-200"
                        style={{backgroundColor: RED}}
                        onMouseEnter={e => (e.currentTarget.style.backgroundColor = "#87251B")}
                        onMouseLeave={e => (e.currentTarget.style.backgroundColor = RED)}
                    >
                        Выйти
                    </NavLink>
                </nav>
            </header>

            {/* Page content */}
            <main className="flex-1 pt-16">
                <Outlet/>
            </main>
        </div>
    )
}

export default TopBarLayout