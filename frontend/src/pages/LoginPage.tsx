import OP_logo from "../assets/OP_logo.svg"
import SPbguLogo from "../assets/SPbgu_logo.svg"

function LoginPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-white px-4">

            {/* Panel */}
            <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden border border-gray-200">

                {/* Top red line */}
                <div className="h-1 bg-[#9F2D20]"/>

                <div className="px-10 py-8 flex flex-col gap-6">

                    {/* Branding */}
                    <div className="flex items-center justify-between">

                        {/* Left: OP Logo + OurPaint */}
                        <div className="flex items-center gap-2">
                            <img src={OP_logo} alt="OP Logo" className="h-9"/>
                            <span className="text-lg font-semibold tracking-tight">
                <span className="text-[#9F2D20]">OurPaint</span> Company
              </span>
                        </div>

                        {/* Separator */}
                        <div className="h-10 w-[1px] bg-gray-300 mx-4"/>

                        {/* Right: SPbGU Logo */}
                        <img src={SPbguLogo} alt="SPbGU Logo" className="h-14"/>

                    </div>

                    {/* Divider between logos and title */}
                    <div className="w-full h-[1px] bg-gray-300 my-1"/>

                    {/* Title */}
                    <div className="text-center">
                        <h1 className="text-3xl font-extrabold tracking-tight text-[#9F2D20]">
                            Drone Analytics
                        </h1>

                        <p className="text-sm text-gray-500 mt-1">
                            Система мониторинга и аналитики
                        </p>
                    </div>

                    {/* Form */}
                    <form className="flex flex-col gap-6">

                        {/* Login */}
                        <div>
                            <label className="block text-sm font-medium text-gray-600 mb-1">
                                Логин
                            </label>
                            <input
                                type="text"
                                placeholder="Введите логин"
                                className="
                  w-full px-4 py-2
                  rounded-lg
                  border border-gray-300
                  focus:outline-none
                  focus:ring-2 focus:ring-[#9F2D20]/40
                  transition
                "
                            />
                        </div>

                        {/* Password */}
                        <div>
                            <label className="block text-sm font-medium text-gray-600 mb-1">
                                Пароль
                            </label>
                            <input
                                type="password"
                                placeholder="Введите пароль"
                                className="
                  w-full px-4 py-2
                  rounded-lg
                  border border-gray-300
                  focus:outline-none
                  focus:ring-2 focus:ring-[#9F2D20]/40
                  transition
                "
                            />
                        </div>

                        {/* Forgot password */}
                        <div className="flex justify-end">
                            <button
                                type="button"
                                className="text-sm text-[#9F2D20] hover:underline"
                            >
                                Забыли пароль?
                            </button>
                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            className="
                mt-2 py-3
                rounded-lg
                bg-[#9F2D20]
                text-white font-semibold
                hover:bg-[#87251B]
                transition
                shadow-md hover:shadow-lg
              "
                        >
                            Войти
                        </button>

                    </form>
                </div>
            </div>
        </div>
    )
}

export default LoginPage