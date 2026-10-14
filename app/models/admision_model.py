from .database import get_db

class AdmisionModel:
    @staticmethod
    def listar(q='',estado='',paciente_id=None,profesional_id=None):
        sql="""SELECT a.*,p.nombre,p.documento,f.nombre AS funcionario,f.cargo,b.inicio,b.fin,t.nombre AS tipo_atencion
            FROM admisiones a JOIN pacientes p ON p.id=a.paciente_id
            LEFT JOIN profesionales f ON f.id=a.profesional_id
            LEFT JOIN agenda_bloques b ON b.id=a.slot_id LEFT JOIN tipos_atencion t ON t.id=b.tipo_id
            WHERE a.activo=1 AND p.activo=1 AND (p.nombre LIKE ? OR p.documento LIKE ?)"""
        args=['%'+q+'%','%'+q+'%']
        if estado:
            sql+=' AND a.estado=?';args.append(estado)
        if paciente_id is not None:
            sql+=' AND a.paciente_id=?';args.append(paciente_id)
        if profesional_id is not None:
            sql+=' AND a.profesional_id=?';args.append(profesional_id)
        sql+=" ORDER BY a.fecha,COALESCE(b.inicio,'99:99'),a.creada,a.id"
        return get_db().execute(sql,args).fetchall()
    @staticmethod
    def obtener(id):
        return get_db().execute("""SELECT a.*,p.nombre,p.documento,p.activo AS paciente_activo,f.nombre AS funcionario,f.cargo,b.inicio,b.fin,t.nombre AS tipo_atencion
            FROM admisiones a JOIN pacientes p ON p.id=a.paciente_id
            LEFT JOIN profesionales f ON f.id=a.profesional_id
            LEFT JOIN agenda_bloques b ON b.id=a.slot_id LEFT JOIN tipos_atencion t ON t.id=b.tipo_id WHERE a.id=? AND a.activo=1""",(id,)).fetchone()
