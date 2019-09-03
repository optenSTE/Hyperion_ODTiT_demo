# -*- coding: utf-8 -*-
import math

# MicroOptics FBG-sensor class (either strain and temperature)
class FBG:

    def __init__(self):
        self.id = 0
        self.type = 'os3110'
        self.name = 'NONAME'
        self.t0 = 0.0
        self.wl0 = 0.0
        self.p_min = 0.0
        self.p_max = 65535
        self.wl_min = 1420000
        self.wl_max = 1660000
        self.fg = 0.89  # 0.89 только os3110
        self.ctet = 0.0  # КТЛР подложки os3110
        self.st = 1.87754658264289E-5  # коэффициент для расчета температуры os4100

    def __str__(self):
        print_str = 'Sensor %s Name=%s ID=%s WL0=%.4f T0=%.2f' % (self.type, self.name, self.id, self.wl0, self.t0)
        return print_str

    def get_temperature(self, wl):
        return self.t0 + (wl - self.wl0) / (self.wl0 * self.st)

    def is_power_ok(self, power):
        if self.p_min <= power <= self.p_max:
            return True
        return False


class ODTiT:
    def __init__(self, channel=0):
        self.channel = channel
        self.id = 0  # идентификатор устройства
        self.name = 'NONAME'  # наименование устройства, используется для вывода
        self.channel = 1  # номер порта MicronOptics si255, к которому подключено устройство
        self.sample_rate = 0  # ожидаемое значение частоты поступления данных, Гц

        self.e = 0.0  # модуль Юнга устройства
        self.ctes = 0.0  # КТЛР тела ОДТиТ
        self.size = (0.0, 0.0)  # размер рабочей области (толщина, высота), мм
        self.bend_sens = 0.01  # чувствительность к поперечным нагрузкам, ustr/daN

        self.span_len = 0.0  # длина пролета, м
        self.span_rope_diameter = 0.0  # диаметр троса, м
        self.span_rope_density = 0.0  # погонная масса провода, кг/м
        self.span_rope_EJ = 0.0  # модуль упругости * момент инерции провода

        self.f_min = 0.0  # окно возможных тяжений провода, даН
        self.f_max = 400.0
        self.f_reserve = 1000.0  # запас по тяжению (расширяет диапазон f_min...f_max в обе стороны), даН

        # полином вычисления ожидаемого тяжения Fожид(T) = f2*T^2 + f1*T + f0, где Т-температура
        self.fmodel_f0 = 0
        self.fmodel_f1 = 0
        self.fmodel_f2 = 0

        # полином вычисления стенки гололеда по превышению текущего тяжения над ожидаемым Fextra(Ice) = i2*Ice^2+i1*Ice
        self.icemodel_i1 = 0
        self.icemodel_i2 = 0

        # используются только для проверки принадлежности измерений температурной решетке
        self.t_min = -60.0  # минимальная эксплутационная температура, С
        self.t_max = 60.0  # максимальная эксплутационная температура, С

        self.time_of_flight = 0  # Задержка распространения света в волокне от Прибора до первой решетки Измерителя и обратно

        self.sensors = []  # три решетки - температурная, натяжная левая, натяжная правая
        for i in range(3):
            self.sensors.append(FBG())

    def __str__(self):
        print_str = 'ODTiT device: %s\t%s\t%s\t%s' % (self.name, self.sensors[1].__str__(), self.sensors[2].__str__(), self.sensors[0].__str__())
        return print_str

    def find_yours_wls(self, wls_pm, channel=0):
        """Function checks is this wavelength belongs of
            this ODTiT device (any of optical sensor)

        :param wl_pm: wavelength, pm
        :param channel: channel num for MOI si255
        :return: is the wavelength belongs of this ODTiT device

        """
        wl_sensor0 = None
        wl_sensor1 = None
        wl_sensor2 = None

        # сначала находим температурную решетку и рассчитываем температуру
        cur_t = None
        for wl_pm in wls_pm:
            if not cur_t and self.is_wl_of_temperature_sensor(wl_pm, channel):
                wl_sensor0 = wl_pm
                cur_t = self.get_temperature(wl_pm)

        # имея температуру, находим натяжные решетки
        for wl_pm in wls_pm:
            if cur_t and not wl_sensor1 and self.is_wl_of_strain_sensor(wl_pm, cur_t, 1, channel):
                wl_sensor1 = wl_pm
            elif cur_t and not wl_sensor2 and self.is_wl_of_strain_sensor(wl_pm, cur_t, 2, channel):
                wl_sensor2 = wl_pm

        # ToDo проверяем, что в окно возможных длин волн попадает только один пик

        if wl_sensor0 and wl_sensor1 and wl_sensor2:
            return (wl_sensor0, wl_sensor1, wl_sensor2)
        return False

    def is_wl_of_temperature_sensor(self, wl_pm, channel=0):
        """Function checks is this wavelength belongs of
            this ODTiT device (temperature optical sensor)

        :param wl_pm: wavelength, pm
        :param channel: channel num for MOI si255
        :return: is the wavelength belongs of this ODTiT device

        """

        wl_max = self.sensors[0].wl0 * (1 + (self.t_max - self.sensors[0].t0) * self.sensors[0].st)
        wl_min = self.sensors[0].wl0 * (1 + (self.t_min - self.sensors[0].t0) * self.sensors[0].st)

        ret_value = False
        if min(wl_min, wl_max) <= wl_pm <= max(wl_min, wl_max):
            ret_value = True

        if self.channel > 0 and channel != self.channel:
            ret_value = False

        return ret_value

    def is_wl_of_strain_sensor(self, wl, t, sensor_num, channel=0):
        """For strain sensors os3110 checks is given WL belongs of this ODTiT device

        :param wl: measured strain sensor's wavelength, pm
        :param t: ODTiT device temperature, degC (by os4100 sensor)
        :param sensor_num: 1 or 2 - first or second sensor into ODTiT device
        :param channel: channel num for strain sensor, only for MIO instruments
        :return: is the wavelength belongs of this ODTiT device

        """

        if 1 < sensor_num > 2:
            raise IndentationError('Sensor_num should be 1 or 2')

        # WL = WL_0 * (1 + ((f1 * 10 / (E * S) - (T - Ts1_0) * (CTET - CTES) / 1000000) * FG + (T - Tt_0) * ST));

        wl_min = self.sensors[sensor_num].wl0 * (1 + (((self.f_min - self.f_reserve) * 10 / (self.e * self.size[0] * self.size[1] * 1E-6) - (t - self.sensors[sensor_num].t0) * (
                    self.sensors[sensor_num].ctet - self.ctes) / 1E+6) * self.sensors[sensor_num].fg + (t - self.sensors[0].t0) * self.sensors[0].st))
        wl_max = self.sensors[sensor_num].wl0 * (1 + (((self.f_max + self.f_reserve) * 10 / (self.e * self.size[0] * self.size[1] * 1E-6) - (t - self.sensors[sensor_num].t0) * (
                    self.sensors[sensor_num].ctet - self.ctes) / 1E+6) * self.sensors[sensor_num].fg + (t - self.sensors[0].t0) * self.sensors[0].st))

        ret_value = False
        if min(wl_min, wl_max) <= wl <= max(wl_min, wl_max):
            ret_value = True

        if self.channel > 0 and channel != self.channel:
            ret_value = False

        return ret_value

    def get_temperature(self, wl_temperature_sensor):
        return self.sensors[0].get_temperature(wl_temperature_sensor)

    def get_tension_fav(self, wl_tension_sensor_1, wl_tension_sensor_2, wl_temperature_sensor):
        return self.get_tension_fav_ex(wl_tension_sensor_1, wl_tension_sensor_2, wl_temperature_sensor)[0]

    def get_tension_fav_ex(self, wl_tension_sensor_1, wl_tension_sensor_2,
                           wl_temperature_sensor, return_nan=False):

        return_value = dict()

        return_value.setdefault('T_degC', None)
        return_value.setdefault('eps1_ustr', None)
        return_value.setdefault('eps2_ustr', None)
        return_value.setdefault('F1_N', None)
        return_value.setdefault('F2_N', None)
        return_value.setdefault('Fav_N', None)
        return_value.setdefault('Fbend_N', None)
        return_value.setdefault('Ice_mm', None)

        if not return_nan:
            temperature_value = self.get_temperature(wl_temperature_sensor)

            eps1 = 1E+06 * ((wl_tension_sensor_1 - self.sensors[1].wl0) / self.sensors[1].wl0 - (wl_temperature_sensor - self.sensors[0].wl0) / self.sensors[0].wl0) / self.sensors[
                1].fg + (temperature_value - self.sensors[0].t0) * (self.sensors[1].ctet - self.ctes)
            eps2 = 1E+06 * ((wl_tension_sensor_2 - self.sensors[2].wl0) / self.sensors[2].wl0 - (wl_temperature_sensor - self.sensors[0].wl0) / self.sensors[0].wl0) / self.sensors[
                2].fg + (temperature_value - self.sensors[0].t0) * (self.sensors[2].ctet - self.ctes)

            f1 = (eps1 * self.e * self.size[0] * self.size[1]) / (1E+6 * 1E+6)
            f2 = (eps2 * self.e * self.size[0] * self.size[1]) / (1E+6 * 1E+6)

            f_av = (f1 + f2) / 2

            f_model = 10*(self.fmodel_f0 + self.fmodel_f1*temperature_value + self.fmodel_f2*temperature_value**2)
            f_extra = f_av - f_model

            ice_mm = None
            if self.icemodel_i2 != 0:
                try:
                    ice_mm = (math.sqrt(4*self.icemodel_i2*f_extra/10.0 + self.icemodel_i1**2) - self.icemodel_i1)/(2*self.icemodel_i2)
                except:
                    ice_mm = 0

            return_value['T_degC'] = temperature_value
            return_value['eps1_ustr'] = eps1
            return_value['eps2_ustr'] = eps2
            return_value['F1_N'] = f1
            return_value['F2_N'] = f2
            return_value['Fav_N'] = (f1 + f2) / 2
            return_value['Fbend_N'] = (eps1 - eps2) / (2 * self.bend_sens)
            return_value['Ice_mm'] = ice_mm

        return return_value
