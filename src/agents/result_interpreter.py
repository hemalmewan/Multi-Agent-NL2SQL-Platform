##============================
## Import Required Libraries
##============================
from typing import Dict,Any,Optional,List
from loguru import logger
import time
import plotly.express as px
import pandas as pd

##============================
## Result Interpreter Agent
##============================
class ResultInterpreter:

    def __init__(self,llm):
        self.llm_call=llm
    
    ##==========================================
    ## Check SQL Result can be visualized or not
    ##==========================================
    def _can_visualize(
        self,
        sql_result:List[Dict[str,Any]]
        ):

        if not sql_result:
            return False
        
        sample=sql_result[0]

        numeric_count=0
        categorical_count=0

        for value in sample.values():
            if isinstance(value,(int,float)):
                numeric_count+=1
            else:
                categorical_count+=1
        
        return numeric_count>=1 and categorical_count>=1
    
    ##============================
    ## Detect Chart Type
    ##============================
    def _detect_chart_type(
        self,
        sql_result:List[Dict[str,Any]]
        ) -> str:

            if sql_result is None or len(sql_result)==0:
                logger.warning("No result returned from database")
            
            ## get the SQL columns
            columns=list(sql_result[0].keys())

            if len(columns)>3 and len(sql_result)>1:
                return "table"
            
            if len(columns)>=1 and len(sql_result)==1:
                return "text"
            
            if len(columns)==3:
                if self._is_time_based(sql_result=sql_result):
                    return "line"
                else:
                    return "bar"
            
            if len(columns)==2:
                if self._is_time_based(sql_result=sql_result):
                    return "line"
                elif len(sql_result)<=5:
                    return "pie"
                else:
                    return "bar"
                

    ##=========================================
    ## Check if sql result is time based or not
    ##=========================================
    def _is_time_based(
        self,
        sql_result:List[Dict[str,Any]]
        ) -> bool:

            if not sql_result:
                return False
            
            sample_key=sql_result[0]

            for key,value in sample_key.items():

                key_lower=key.lower()
                if any(key_word in key_lower for key_word in ["date","time","year","month","day"]):
                    return True
            
            return False
    
    ##=============================
    ## Extrect the Column names
    ##=============================
    def _extract_columns(self, sql_result):
        numeric, categorical, time_cols = self._classify_columns(sql_result)

        if time_cols and numeric:
            x = time_cols[0]
            y = numeric[0]
            group = categorical[0] if categorical else None
            return x, y, group

        if len(categorical) >= 2 and numeric:
            x = categorical[0]
            group = categorical[1]
            y = numeric[0]
            return x, y, group

        if len(categorical) >= 1 and numeric:
            return categorical[0], numeric[0]

        logger.warning("Could not determine chart axes properly")
        return None, None, None
        
    ##=========================================================
    ## Classify Columns as numeric, categorical and time based
    ##=========================================================
    def _classify_columns(
        self,
        sql_result:List[Dict[str,Any]]
        ):

        sample=sql_result[0]
        numeric_cols=[]
        categorical_cols=[]
        time_based_cols=[]


        for column,value in sample.items():
            col_lower=column.lower()

            if isinstance(value,(int,float)):
                numeric_cols.append(column)
            
            elif any(col in col_lower for col in ["date","time","day","month","year"]):
                time_based_cols.append(column)
            
            else:
                categorical_cols.append(column)
        
        return numeric_cols,categorical_cols,time_based_cols
       
    
    ##=====================================
    ## Generate chart based on sql result
    ##=====================================
    def _chart_generator(
        self,
        user_query:str,
        sql_result: List[Dict[str, Any]]
        ):

        if not sql_result:
            logger.warning("No data available from database")
            return {
                "type": "text",
                "content": "No data available."
            }

        chart_type = self._detect_chart_type(sql_result=sql_result)
        logger.info("Chart type detected as: {}".format(chart_type))

        if chart_type == "text":
            logger.info("Generating text summary via LLM")
            summary = self._generate_text_summary(user_query=user_query,
            sql_result=sql_result)

            return {
                "type": "text",
                "content": summary
            }

        if chart_type == "table":
            logger.info("Returning table visualization")
            sql_result=pd.DataFrame(sql_result)
            return {
                "type": "table",
                "data":sql_result.head(1),
                "content": len(sql_result)
            }

        try:
            columns = self._extract_columns(sql_result)
            sql_result=pd.DataFrame(sql_result)

            if len(columns) == 2:
                x_key, y_key = columns

                if chart_type == "bar":
                    fig = px.bar(
                        sql_result, 
                        x=x_key, 
                        y=y_key,
                        title=f"Bar chart of {y_key} by {x_key}"
                    )


                elif chart_type == "line":
                    fig = px.line(
                        sql_result, 
                        x=x_key, 
                        y=y_key,
                        title=f"Line chart of {y_key} by {x_key}"
                    )

                elif chart_type == "pie":
                    fig = px.pie(
                        sql_result, 
                        names=x_key, 
                        values=y_key,
                        title=f"Pie chart of {x_key} by {y_key}"
                    )

                else:
                    logger.warning(f"Unsupported chart type: {chart_type}")
                    return {
                        "type": "table",
                        "content": sql_result
                    }

            elif len(columns) == 3:
                x_key, y_key, group_key = columns

                if chart_type == "bar":
                    fig = px.bar(
                        sql_result,
                        x=x_key,
                        y=y_key,
                        color=group_key,
                        barmode="group",
                        title=f"Bar chart of {y_key} by {x_key} and {group_key}"
                    )

                elif chart_type == "line":
                    fig = px.line(
                        sql_result,
                        x=x_key,
                        y=y_key,
                        color=group_key,
                        title=f"Line chart of {y_key} by {x_key} and {group_key}"
                    )

                else:
                    logger.warning(f"Chart type {chart_type} not ideal for 3 columns")
                    return {
                        "type": "table",
                        "content": sql_result
                    }

            else:
                logger.warning("Unsupported column structure → fallback to table")
                return {
                    "type": "table",
                    "content": sql_result
                }
            
            fig.update_layout(
                title_x=0.5,
                title_font=dict(
                    size=16
                )
            )

            return {
                "type": "chart",
                "chart_type": chart_type,
                "figure": fig.show()
            }
            

        except Exception as e:
            logger.error(f"Chart generation failed: {e}")

            return {
                "type": "table",
                "content": sql_result
            }
    
    ##===================================
    ## Generate text summary using LLM
    ##===================================
    def _generate_text_summary(
        self, 
        user_query:str,
        sql_result:List[Dict[str,Any]]
        ):

        prompt = f"""
        You are an expert data analyst.
        Your goal is to provide a short, clear, human-readable explanation of the SQL query result.

        User query: 
        {user_query}
        
        SQL Result:
        {sql_result}

        Keep it concise and user-friendly.
        """

        try:
            response = self.llm_call.generate(prompt)
            return response.get("response", "No summary generated.")
        except Exception as e:
            logger.error(f"LLM summary failed: {e}")
            return "Unable to generate summary."





    