from flask import g 

class Season:

    id = None
    signup_limit = 0
    signups_open = False


    def __init__(self, id):
        self.id = id
        

    def remove_signups(self, users):
        query = """
        DELETE FROM signups 
        WHERE season_id = ?
        AND user_id IN (?)
        """

        for user_id in users:
            values = (self.id, user_id)
            cur = g.db.execute(query, values)
            if not cur.rowcount:
                g.db.rollback()
                return False

        g.db.commit()
        return True


    def add_to_division(self, division, users):
        if division <= 0:
            return False

        query = """
        UPDATE signups SET division = ?
        WHERE season_id = ? 
        AND user_id = ?
        """
        for user_id in users:
            values = (division, self.id, user_id)
            cur = g.db.execute(query, values)
            if not cur.rowcount:
                g.db.rollback()
                return False

        g.db.commit()
        return True


    def remove_from_division(self, user_id):
        query = """
        UPDATE signups SET division = NULL
        WHERE season_id = ?
        AND user_id = ?
        """
        values = (self.id, user_id)
        cur = g.db.execute(query, values)
        if cur.rowcount:
            g.db.commit()
            return True

        g.db.rollback()
        return False


    @staticmethod
    def remove_signup(season_id, user_id):
        query = """
        DELETE FROM signups
        WHERE season_id = ?
        AND user_id = ?
        """
        values = (season_id, user_id)
        cur = g.db.execute(query, values)
        if cur.rowcount:
            g.db.commit()
            return True
        
        g.db.rollback()
        return False


    def get_unasigned_signup_list(self):
        query = """
        SELECT user_id, username FROM signups
        LEFT JOIN users ON users.id = user_id
        WHERE season_id = ? AND signups.division IS NULL
        """
        cur = g.db.execute(query, (self.id))
        return cur.fetchall()


    def get_signups(self):
        from wsw import query_db
        query = """
        SELECT users.id, username, division FROM signups
        LEFT JOIN users ON users.id = user_id
        WHERE season_id = ?
        """
        return query_db(query, (self.id))


    def get_waiting_list(self):
        from wsw import query_db
        query = """
        SELECT users.id, users.username, signups.division
        FROM signups
        LEFT JOIN users ON users.id = signups.user_id
        WHERE signups.season_id = ? AND signups.division IS NULL
        """
        return query_db(query, (self.id))

    def get_map_pool(self):
        from wsw import query_db
        query = """
        SELECT id, name FROM season_maps
        LEFT JOIN maps ON maps.id = map_id
        WHERE season_id = ?
        """
        return query_db(query, (self.id))

    def get_maps_not_in_pool(self):
        query = """
        SELECT id, name FROM maps
        WHERE id NOT IN
        (SELECT map_id FROM season_maps WHERE season_id = ?)
        """
        cur = g.db.execute(query, (self.id))
        return cur.fetchall()

    def get_users_for_signup(self):
        query = """
        SELECT id, username FROM users
        WHERE id NOT IN
        (SELECT user_id FROM signups WHERE season_id = ?)
        """
        return g.db.execute(query, (self.id))

    def get_divisions(self):
        # find populated divisions for a season
        # TODO pull the highest division number and return all divisions based
        # on that number
        query = """
        SELECT DISTINCT division FROM signups
        WHERE season_id = ? ORDER BY division ASC
        """
        cur = g.db.execute(query, (self.id))
        division_numbers = cur.fetchall()

        # return None if no divisions are populated
        if not division_numbers:
            return None

        divisions = []
        for i in division_numbers:
            i = i[0]
            if i:
                divisions.append(self.get_division(i))

        return divisions


    def get_division(self, division):
        from wsw import query_db
        query = """
        SELECT users.id, username, division FROM signups
        LEFT JOIN users ON users.id = user_id
        WHERE season_id = ?
        AND division = ?
        """
        values = (self.id, division)
        return query_db(query, values)


    def load(self, id=None):
        from wsw import query_db
        if not id:
            if not self.id:
                return
            id = self.id
        query = 'SELECT * FROM seasons WHERE id = ?'
        data = query_db(query, (id), True)
        self.signup_limit = data['signup_limit']
        self.signups_open = data['signups_open']


    @staticmethod
    def get_current_season_id():
        query = 'SELECT id FROM seasons ORDER BY id DESC LIMIT 1'
        cur = g.db.execute(query)
        season = cur.fetchone()
        if season:
            return season[0]
        return None


    @staticmethod
    def get_seasons_list():
        from wsw import query_db
        query = 'SELECT id FROM seasons'
        return query_db(query)


