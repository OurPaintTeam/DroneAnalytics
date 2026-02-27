import AlexPhoto from "../assets/Alex.jpg"
import TimPhoto from "../assets/Tim.jpg"
import EugenPhoto from "../assets/Eugen.jpg"
import NikitaPhoto from "../assets/Nikita.jpg"

import OP_logo from "../assets/OP_logo.svg"
import SPbguLogo from "../assets/SPbgu_logo.svg"

const teamMembers = [
    { name: "Alex", role: "Архитектор", photo: AlexPhoto },
    { name: "Tim", role: "Фронтенд разработчик", photo: TimPhoto },
    { name: "Eugen", role: "Бекенд тимлид", photo: EugenPhoto },
    { name: "Nikita", role: "Бекенд разработчик", photo: NikitaPhoto },
]

const AboutPage = () => {
    return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-8">

            {/* Title */}
            <h1 className="text-3xl md:text-4xl font-extrabold text-[#9F2D20] mb-4 text-center">
                About Drone Analytics
            </h1>
            <p className="text-gray-700 text-center max-w-2xl mb-12">
                Этот сайт создан для аналитики логов с дронов. Он позволяет визуализировать события, телеметрию и команды,
                а также анализировать безопасность полетов. Наш инструмент помогает эффективно контролировать работу дронов и выявлять ошибки на ранних этапах.
            </p>

            {/* Command */}
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Наша команда</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 mb-12">
                {teamMembers.map((member) => (
                    <div key={member.name} className="flex flex-col items-center bg-white rounded-xl shadow-lg p-4">
                        <img
                            src={member.photo}
                            alt={member.name}
                            className="w-24 h-24 rounded-full object-cover mb-3"
                        />
                        <h3 className="font-semibold text-gray-800">{member.name}</h3>
                        <p className="text-gray-600 text-sm text-center">{member.role}</p>
                    </div>
                ))}
            </div>

            {/* Sponsors */}
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Наши спонсоры</h2>
            <div className="flex items-center gap-12">
                <div className="flex flex-col items-center">
                    <img src={OP_logo} alt="OutPaint Company" className="h-16 mb-2" />
                    <span className="text-gray-700 font-medium text-sm">OurPaint Company</span>
                </div>
                <div className="flex flex-col items-center">
                    <img src={SPbguLogo} alt="SPbGU" className="h-16 mb-2" />
                    <span className="text-gray-700 font-medium text-sm">SPbGU</span>
                </div>
            </div>
        </div>
    )
}

export default AboutPage