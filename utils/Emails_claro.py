import os
from functools import reduce
import string
from datetime import datetime
from pyspark.sql import SparkSession, SQLContext
from pyspark.sql.types import StringType
from pyspark.sql.functions import col, concat, lit, upper, regexp_replace, expr, length, size, split, lower, when

spark = SparkSession \
    .builder.appName("Trial") \
    .getOrCreate()
spark.conf.set("mapreduce.fileoutputcomitter.marksuccessfuljobs","false")

sqlContext = SQLContext(spark)

### Proceso con todas las funciones desarrolladas
def Function_Complete(path, output_directory, partitions):

    Data_Frame = First_Changes_DataFrame(path)

    Data_Email = Email_Data(Data_Frame)
    Type = "Emails"
    Data_Email = Demographic_Proccess_Emails(Data_Email, output_directory, partitions)
    Save_Data_Frame(Data_Email, output_directory, partitions, Type)

### Cambios Generales
def First_Changes_DataFrame(Root_Path):
    
    files = [os.path.join(Root_Path, file) for file in os.listdir(Root_Path) if file.endswith(".csv")]
    Data_Root = spark.read.option("header", "true").option("sep", ";").csv(files)

    DF = Data_Root.select([col(c).cast(StringType()).alias(c) for c in Data_Root.columns])

    potencial = (col("5_") == "Y") & (col("3_") == "BSCS")
    churn = (col("5_") == "Y") & (col("3_") == "RR")
    provision = (col("5_") == "Y") & (col("3_") == "ASCARD")
    prepotencial = (col("6_") == "Y") & (col("3_") == "BSCS")
    prepotencial_especial = (col("6_") == "Y") & (col("3_") == "BSCS") & (col("12_") == "PrePotencial Convergente Masivo_2")
    prechurn = (col("6_") == "Y") & (col("3_") == "RR")
    preprovision = (col("6_") == "Y") & (col("3_") == "ASCARD")
    castigo = col("7_") == "Y"
    potencial_a_castigar = (col("5_") == "N") & (col("6_") == "N") & (col("7_") == "N") & (col("43_") == "Y")
    marcas = col("13_")

    DF = DF.withColumn("Marca", when(potencial, "Potencial")\
            .when(churn, "Churn")\
            .when(provision, "Provision")\
            .when(prepotencial, "Prepotencial")\
            .when(prepotencial_especial, "Prepotencial Especial")\
            .when(prechurn, "Prechurn")\
            .when(preprovision, "Preprovision")\
            .when(castigo, "Castigo")\
            .when(potencial_a_castigar, "Potencial a Castigar")\
            .otherwise(marcas))

    return DF

### Renombramiento de columnas
def Renamed_Column(Data_Frame):

    Data_Frame = Data_Frame.withColumnRenamed("1_", "identificacion")
    Data_Frame = Data_Frame.withColumnRenamed("2_", "cuenta")

    return Data_Frame

### Proceso de guardado del RDD
def Save_Data_Frame (Data_Frame, Directory_to_Save, partitions, Type):

    now = datetime.now()
    Time_File = now.strftime("%Y%m%d_%H%M")
    Time_File_File = now.strftime("%Y%m%d")
    Type_File = f"Demograficos - Claro_{Type}_"
    
    output_path = f'{Directory_to_Save}{Type_File}{Time_File}'
    partitions = int(partitions)

    Data_Frame = Data_Frame.withColumn("cruice", concat(col("cuenta"), col("dato")))
    Data_Frame = Data_Frame.dropDuplicates(["cruice"])

    Data_Frame = Data_Frame.select("identificacion", "cuenta", "Origen", "Deuda", "dato", "Marca")
    Data_Frame = Data_Frame.withColumn("cuenta", concat(col("cuenta"), lit("-")))

    Data_Frame = Data_Frame.orderBy(col("dato"))

    Data_Frame.repartition(partitions).write.mode("overwrite").option("header", "true").option("delimiter",";").csv(output_path)

    for root, dirs, files in os.walk(output_path):
            for file in files:
                if file.startswith("._") or file == "_SUCCESS" or file.endswith(".crc"):
                    os.remove(os.path.join(root, file))
        
    for i, file in enumerate(os.listdir(output_path), start=1):
        if file.endswith(".csv"):
            old_file_path = os.path.join(output_path, file)
            new_file_path = os.path.join(output_path, f'Demograficos Claro {Type} {Time_File_File} {i}.csv')
            os.rename(old_file_path, new_file_path)

    return Data_Frame

def Email_Data(Data_):

    columns_to_stack = ["47_", "48_", "49_", "50_", "51_"] #EMAIL and Phone X (1-4)

    all_columns_to_stack = columns_to_stack

    columns_to_drop_contact = all_columns_to_stack
    stacked_contact_data_frame = Data_.select("*", *all_columns_to_stack)

    stacked_contact_data_frame = stacked_contact_data_frame.select(
        "*",
        expr(f"stack({len(all_columns_to_stack)}, {', '.join(all_columns_to_stack)}) as dato")
    )

    Data_ = stacked_contact_data_frame.drop(*columns_to_drop_contact)

    return Data_

def Remove_Dots(dataframe, column):

    dataframe = dataframe.withColumn(column, regexp_replace(col(column), "[.-]", ""))
    
    return dataframe

def Demographic_Proccess_Emails(Data_, Directory_to_Save, partitions):

    Data_ = Data_.withColumn("Origen", col("3_"))
    Data_ = Data_.withColumn("Deuda", col("9_").cast("double"))
    Data_ = Data_.withColumn("Deuda", regexp_replace("Deuda", "\\.", ","))
    
    Data_ = Data_.select("1_", "2_", "22_", "Origen", "Deuda", "dato", "Marca")

    Data_ = Data_.withColumn("1_", regexp_replace("1_", "[^0-9]", ""))
    Data_ = Data_.filter(col("1_").cast("int").isNotNull())
    Data_ = Data_.withColumn("1_", col("1_").cast("int"))
    
    character_list = list(string.ascii_uppercase)
    Punctuation_List = ["\\*"]
    character_list = character_list + Punctuation_List
    
    Data_ = Data_.withColumn("1_", upper(col("1_")))

    for character in character_list:
        Data_ = Data_.withColumn("1_", regexp_replace(col("1_"), character, ""))
        Data_ = Data_.withColumn("2_", regexp_replace(col("2_"), character, ""))
    
    Data_ = Function_Filter_Email(Data_)
    Data_ = Data_.withColumn("cruice", concat(col("2_"), col("dato")))
    Data_ = Data_.dropDuplicates(["cruice"])

    Data_ = Remove_Dots(Data_, "1_")
    Data_ = Remove_Dots(Data_, "2_")

    Data_ = Renamed_Column(Data_)

    Data_ = Data_.select("identificacion", "cuenta", "Origen", "Deuda", "dato", "Marca")

    return Data_

def Function_Filter_Email(Data_):

    Data_ = Data_.withColumn(
        "Tipologia",
        when(length(split(col("dato"), "@")[0]) < 6, "ERRADO")  # Check the length of the part before the '@'
        .when(size(split(col("dato"), "@")) == 2, "CORREO UNICO")
        .when(size(split(col("dato"), "@")) >= 3, "CORREOS SIN DELIMITAR")
        .otherwise("ERRADO")
    )

    Data_ = Data_.filter(col("dato").contains("@claro.com"))

    list_email_replace = [
        "notiene", "nousa", "nobrinda", "000@00.com.co", "nolorecuerda", "notengo", "noposee",
        "nosirve", "notien", "noutili", "nomanej", "nolegust", "nohay", "nocorreo", "noindic",
        "nohay", "@gamil", "pendienteconfirmar", "sincorr", "pendienteporcrearclaro", "correo.claro",
        "crearclaro", ":", "|", " ", "porcrear", "+", "#", "@xxx", "-", "suministra",
        "factelectronica", "nodispone", "claro.movil", "sicorreo", "pruebasrio"
    ]

    email_set = set(list_email_replace)

    Data_ = Data_.withColumn("dato", lower(col("dato")))

    contains_any_expr = reduce(
        lambda acc, word: acc | col("dato").contains(word),
        email_set,
        lit(False)
    )

    # Actualizar la columna Tipologia
    Data_ = Data_.withColumn(
        "Tipologia",
        when(contains_any_expr, "ERRADO")
        .otherwise(col("Tipologia"))
        )
    
    Data_ = Data_.filter(col("dato") != "@")
    Data_ = Data_.filter(col("Tipologia") != "ERRADO")

    return Data_


folder_path = "C:/Users/c.operativo/Downloads/"
partitions = 1
Path = "D:/BASES CLARO/2024/09. Septiembre/Bases"

Function_Complete(Path, folder_path, partitions)