#include <iostream>
#define INFO true

namespace Commands{
	struct TurnOn{};
	struct TurnOff{};
	struct SetTemperature{
		int temperature;
	};
}

namespace Devices{
	struct AirConditioner{
	private:
		bool is_on;
		int temperature;
	public:
		void Execute(Commands::TurnOn){
			is_on = true;
			if(INFO){
				std::cerr << "AirConditioner turned on." << std::endl;
				std::cerr << "Current temperature: " << temperature << "°C" << std::endl;
			}
		}
		void Execute(Commands::TurnOff){
			is_on = false;
			if(INFO){
				std::cerr << "AirConditioner turned off." << std::endl;
			}
		}
		void Execute(Commands::SetTemperature cmd){
			temperature = cmd.temperature;
			if(INFO){
				std::cerr << "AirConditioner temperature set to " << temperature << "°C." << std::endl;
			}
		}
	};
}

int main() {
    return 0;
}
