from .database import get_db

class AgendaModel:
    @staticmethod
    def tipos():
        return get_db().execute('SELECT * FROM tipos_atencion WHERE activo=1 ORDER BY nombre').fetchall()
    @staticmethod
    def listar(desde,hasta,profesional_id=None,tipo_id=None):
        return get_db().execute("""SELECT b.*,p.nombre AS funcionario,p.especialidad,t.nombre AS tipo,
            (SELECT COUNT(*) FROM admisiones a WHERE a.slot_id=b.id AND a.activo=1 AND a.estado!='cancelado') AS ocupados
            FROM agenda_bloques b JOIN profesionales p ON p.id=b.profesional_id JOIN tipos_atencion t ON t.id=b.tipo_id
            WHERE b.activo=1 AND p.activo=1 AND b.fecha BETWEEN ? AND ?
            AND (? IS NULL OR b.profesional_id=?) AND (? IS NULL OR b.tipo_id=?)
            ORDER BY b.fecha,b.inicio,p.nombre""",(desde,hasta,profesional_id,profesional_id,tipo_id,tipo_id)).fetchall()
    @staticmethod
    def obtener(id):
        return get_db().execute("""SELECT b.*,p.nombre AS funcionario,p.especialidad,p.activo AS profesional_activo,t.nombre AS tipo,
            (SELECT COUNT(*) FROM admisiones a WHERE a.slot_id=b.id AND a.activo=1 AND a.estado!='cancelado') AS ocupados
            FROM agenda_bloques b JOIN profesionales p ON p.id=b.profesional_id JOIN tipos_atencion t ON t.id=b.tipo_id
            WHERE b.id=? AND b.activo=1""",(id,)).fetchone()
