"""Evaluation for test_building_heating_demand_dummy_heater."""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn

with open("C:\\Users\\k.rieck\\HiSim\\tests\\test_building_heating_demand_dummy_heater_all_tabula_energy_needs.csv", "r") as myfile:
    lines = myfile.readlines()[1:]
    print(len(lines))

if len(lines)  == 0:
    pass
    print("file is empty. nothing to analyze.")
else:
    building_codes = []
    ratios = []
    countries = []

    for index,line in enumerate(lines):
        splitted_line = line.split(";")
        building_code = splitted_line[0]
        country = building_code[0:2]

        ratio_hp_tabula = splitted_line[-1]
        ratio_hp_tabula_floats = float(ratio_hp_tabula)
        building_codes.append(building_code)
        ratios.append(ratio_hp_tabula_floats)
        countries.append(country)


    tabula_countries = list(set(countries))
    list_of_indices = []
    list_of_ratios = []
    for index_1, tabula_country in enumerate(tabula_countries):
        list_of_indices_of_one_country = []
        list_of_ratios_of_one_country = []
        for index_2, country in enumerate(countries):
            if tabula_country == country:
                list_of_indices_of_one_country.append(index_2)
                list_of_ratios_of_one_country.append(ratios[index_2])

        list_of_indices.append(list_of_indices_of_one_country)
        list_of_ratios.append(list_of_ratios_of_one_country)



    max_length_of_list_of_ratios = max(len(list) for list in list_of_ratios)

    for index, list_in_list_of_ratios in enumerate(list_of_ratios):
        if len(list_in_list_of_ratios) < max_length_of_list_of_ratios:
            length_difference = max_length_of_list_of_ratios - len(list_in_list_of_ratios)
            list_of_ratios[index] = list_in_list_of_ratios +  (list(np.repeat(np.nan, length_difference)))


    dictionary_countries_and_indices = dict(zip(tabula_countries, list_of_indices))
    dictionary_countries_and_ratios = dict(zip(tabula_countries, list_of_ratios))

    df = pd.DataFrame(dictionary_countries_and_ratios, index=["first_try"] *232)

    df.index.name="Index Name"
    df.columns.name="Countries"
    plt.figure(figsize=(5,5))

    print(df)
    seaborn.boxplot(data=df)
    seaborn.swarmplot(data=df)
    plt.axhline(y=1, color="red")
    plt.title("Heating Test")
    plt.ylabel("Ratio Heating Need Dummy Heater/Tabula")
    plt.axis([-1,22,0,40])
    plt.xlabel("Country")
    plt.show()

