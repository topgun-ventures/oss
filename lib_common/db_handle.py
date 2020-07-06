import os

from muttlib.dbconn import PgClient

db = PgClient(
    username=os.getenv("DB_USERNAME"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    password=os.getenv("DB_PASS"),
)


def create_tables(project_dir, tables):
    sql_path = os.path.join(project_dir, "sql", "{}.sql")
    for t in tables:
        query = open(sql_path.format(t), "r").read()
        db.execute("DROP TABLE IF EXISTS {} CASCADE".format(t))
        db.execute(query)


def insert_values(df, table_name, stats_dict=None):
    if not stats_dict:
        stats_dict = {k: k for k in df.columns}
    insert_df = df[list(stats_dict.keys())]
    insert_df.rename(columns=stats_dict, inplace=True)

    db.insert_from_frame(insert_df, table_name)

    return None


def insert_df(df, table, stats_dict, id_col, id_table_col="id"):
    query = "select {} from {}".format(id_table_col, table)
    ids_inserted_df = query_to_frame(query)
    ids_inserted = []
    if not ids_inserted_df.empty:
        ids_inserted = ids_inserted_df[id_table_col].tolist()
    df[id_col] = df[id_col].astype(int)
    df_to_insert = df[~df[id_col].isin(ids_inserted)]
    if not df_to_insert.empty:
        insert_values(df_to_insert, table, stats_dict)


def query_to_frame(query):
    df = db.to_frame(query)
    return df
