""" Various postgres-specific helpers, mostly dependent on django orm setup
"""


def do_sql_load_file(copy_sql, the_file, commit=True):
    if isinstance(the_file, str):
        f = open(the_file)
    else:
        f = the_file
    from django.db import connection, transaction
    cursor = connection.cursor()
    ## The very postgresql-specific stuff (also, namespace funhorror)
    cursor.cursor.cursor.copy_expert(copy_sql, f)
    if commit:
        transaction.commit_unless_managed()


def py_to_psqls(item):
    """ Convert the provided python object into a postgres-dumpfile-compatible
    string """
    ## XXX: additional type-specific processing might be requred
    if item == None:
        return 'NULL'
    return str(item)


class ModelToDump(object):
    """ A helper class to convert a django orm Model into a sql / data file
    for loading into the database """

    tfile = None

    def __init__(self, model, the_file=None, write_sql=False):
        self.model = model
        self.write_sql = write_sql
        mm = self.model._meta
        self.aclist = [
            f.get_attname_column()
            for f in mm.fields if not f.primary_key]
        self.attrlist = [attname for attname, column in self.aclist]
        if isinstance(the_file, str):
            self.tfile = open(the_file, 'w')
        else:  # isinstance(the_file, file):
            self.tfile = the_file
        if write_sql:
            self.tfile.write(self.get_copy_sql())

    def get_copy_sql(self):
        """ Returns the corresponding SQL `COPY` statement for the model """
        mm = self.model._meta
        # TODO: use '\\N' for that purpose.
        return (
            "COPY %s (%s) FROM stdin WITH DELIMITER AS '\t' NULL AS"
            " 'NULL';") % (
                mm.db_table,
                ', '.join('"%s"' % (cn,) for an, cn in self.aclist))

    def get_dumpline(self, minstance):
        """ Returns a line with the data from the model instance """
        vals = (getattr(minstance, an, None) for an in self.attrlist)
        return '\t'.join(py_to_psqls(val) for val in vals)

    def write_instance(self, minstance):
        """ Writes the instance to the associated file (assuming that the
        file was provided) """
        return self.tfile.write(self.get_dumpline(minstance) + "\n")

    def finalize(self):
        """ Close the file, writing ending sequence if necessary """
        if self.write_sql:
            self.tfile.write('\\.\n')
        self.tfile.close()
