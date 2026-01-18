from gun import Gun

class Soldier:
    def __init__(self, name, gun = None):
        self.name = name 
        self.gun =  gun
    
    def change_gun(self, new_gun):
        self.gun = new_gun
        print("{} has a new gun {}".format(self.name, self.gun.gun_type))

    def add_gun_bullets(self, bullets_num):
        print("{} add {} bullets".format(self.name, bullets_num))
        self.gun.add_bullets(bullets_num)
    
    def shoot(self):
        print("{} is shooting".format(self.name))
        self.gun.shoot()


if __name__ == "__main__":
    gun = Gun("ak47")
    soldier = Soldier("Tom", gun)
    soldier.add_gun_bullets(10)
    soldier.shoot()
