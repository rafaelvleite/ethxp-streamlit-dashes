#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 28 20:38:48 2022

@author: hack-rafa

"""

description = "Deribit ETH Weekly Options"


def run():
    
    import pandas as pd
    import streamlit as st
    st.set_page_config(layout = "wide")
    import altair as alt
    from urllib.error import URLError
    import s3fs
    import datetime
    import seaborn as sns
    
    
    #Connecting to AWS through smart_open python package and getting the data
    @st.experimental_memo(ttl=None, show_spinner = True)
    def load_data():
        fs = s3fs.S3FileSystem(anon=False)
        
        with fs.open("ethxp/df6a.parquet", 'rb') as f:
            df = pd.read_parquet(f)

        df.set_index('instrument_name', inplace=True)
    
        return df

    
    try:
        # Load data
        df = load_data()
        #df = dfMonthly.copy()
        
        # Sidebar Option Type
        optionType = st.sidebar.radio(
        "Want to check Calls or Puts?",
        ('Call', 'Put'))
    
        if optionType == 'Call':
            optionType = 'call'
        else:
            optionType = 'put'
            
        data = df[df['option_type'] == optionType].copy()
    
        # Sidebar Date
        datesList = list(data['expiration_datetime'].unique())
        datesListFormatted = []
        for dateIte in datesList:
            datesListFormatted.append(datetime.datetime.fromtimestamp(dateIte.astype(datetime.datetime)/1000000000))
        
        datesListFormatted = [i.replace(hour=0) for i in datesListFormatted]
        datesListFormatted.sort()
        datesListFormatted.reverse()
        
        selectedDate = st.sidebar.selectbox(
            "Pick an Expiry Date:",
            datesListFormatted
        )
        
        if selectedDate:
            data = data[(data['expiration_datetime'] >= selectedDate) & (data['expiration_datetime'] <= selectedDate + datetime.timedelta(1))]
        else:
            data = data[(data['expiration_datetime'] >= datesListFormatted[0]) & (data['expiration_datetime'] <= datesListFormatted[0] + datetime.timedelta(1))]
            
        ethLowerLimit = round(data.index_price.min())
        ethUpperLimit = round(data.index_price.max())
        ethMean = round(data.index_price.mean())
        ethStd = round(data.index_price.std())
        
        
        st.sidebar.write("ETH with prices between {} and {} in this period, with average of {} and standard deviation of {}.".format(ethLowerLimit, ethUpperLimit, ethMean, ethStd))
        
        # Sidebar Strikes
        strikesList = list(data.strike.unique())
        strikesList.sort()
        
        centerStrikeIndex = min(range(len(strikesList)), key=lambda i: abs(strikesList[i]-ethMean))
        indexRange = list(range(centerStrikeIndex -3, centerStrikeIndex + 4))
        selectedStrikes = strikesList[indexRange[0]-1:indexRange[-1]]

        container = st.sidebar.container()
        allStrikes = st.sidebar.checkbox("Select 7 centered strikes", value=True)
        
        if allStrikes:
            strikes = container.multiselect("Select one or more strikes:",
                 strikesList,selectedStrikes)
        else:
            strikes = container.multiselect("Select one or more strikes:",
                strikesList)
        
        if not strikes:
            st.sidebar.error("Please select at least one strike.")
        else:
            data = data[data['strike'].isin(strikes)].copy()
        
        # Prepare Data
        data['ethInstrument'] = "ETH"
        data = data.reset_index()
            
        # Render
        st.write("### Past Data for Deribit ETH Weekly Options", data.sort_index())
        
        logarithmic = st.checkbox('Logarithmic Scale')
        if logarithmic: 
            chartScale1 = alt.Scale(type="log")
            chartScale2 = alt.Scale(domain=[ethLowerLimit, ethUpperLimit], type="log")
        else:
            chartScale1 = alt.Scale(type="time")
            chartScale2 = alt.Scale(domain=[ethLowerLimit, ethUpperLimit], type="time")
    
        chart1 = (
            alt.Chart(data)
            .mark_line(interpolate='basis')
            .encode(
                alt.X("datetime:T", title='Date'),
                alt.Y(
                    "price:Q", 
                    title='Instrument Price (ETH)',
                    scale=chartScale1,
                    ),
                color=alt.Color('instrument_name:N', scale=alt.Scale(range=sns.color_palette(n_colors=len(data.index.unique().values)).as_hex())),
                #strokeDash='instrument_name:N',
            )
        )
        
        chart2 = (
            alt.Chart(data)
            .mark_line(interpolate='basis', color='#57A44C')
            .encode(
                alt.X("datetime:T"),
                alt.Y("index_price:Q", 
                title='ETH Price (USD)', 
                scale=chartScale2
                ), 
                color=alt.Color('ethInstrument:N', scale=alt.Scale(range=['#57A44C'])),
            )
        )
        
        # Create a selection that chooses the nearest point & selects based on x-value
        nearest = alt.selection(type='single', nearest=True, on='mouseover',
                                fields=['datetime'], empty='none')
        
        
        # Transparent selectors across the chart. This is what tells us
        # the x-value of the cursor
        selectors = alt.Chart(data).mark_point().encode(
            x='datetime:T',
            opacity=alt.value(0),
            tooltip=alt.value(None),
        ).add_selection(
            nearest
        )
        
        # Draw points on the line, and highlight based on selection
        points = chart1.mark_point().encode(
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
            y=alt.Y("price:Q", 
                    axis=alt.Axis(labels = False, ticks=False, title = "")
                    ),
        )
        points2 = chart2.mark_point().encode(
            opacity=alt.condition(nearest, alt.value(1), alt.value(0)),
        )
        
        # Draw text labels near the points, and highlight based on selection
        text = chart1.mark_text(align='left', dx=5, dy=-5).encode(
            text=alt.condition(nearest, 'price:Q', alt.value(' ')),
            y=alt.Y("price:Q", 
                    axis=alt.Axis(labels = False, ticks=False, title = "")
                    ),
        )
        text2 = chart2.mark_text(align='left', dx=5, dy=-5).encode(
            text=alt.condition(nearest, 'index_price:Q', alt.value(' ')),
        )
        
        # Draw a rule at the location of the selection
        rules = alt.Chart(data).mark_rule(color='gray').encode(
            x='datetime:T',
        ).transform_filter(
            nearest
        )
            
                
        # Put all layers into a chart and bind the data
        c = alt.layer(chart1, chart2, selectors, points, points2, rules, text, text2).resolve_scale(
            y = 'independent'
        ).configure_axisRight(
            titleColor='#1F77B4'
        ).configure_axisLeft(
            titleColor='#57A44C'
        ).properties(
            width=600, height=300
        )
            
        st.altair_chart(c, use_container_width=True)
        
    
    except URLError as e:
        st.error(
            """
            **This demo requires internet access.**
            Connection error: %s
        """
            % e.reason
        )
            

if __name__ == "__main__":
   run()